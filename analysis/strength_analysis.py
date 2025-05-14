#!/usr/bin/env python
# coding: utf-8

# # Concrete Mix Strength Classification Analysis
# 
# This notebook analyzes the relationships between concrete mix compositions and their strength classifications.
# It focuses specifically on mixes with 28-day strength results and explores clustering based on composition.

# ## Setup and Database Connection

import os
import sys
import django
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import plotly.express as px
import plotly.graph_objects as go

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
sys.path.append('c:/Users/anil_/Documents/concrete_mix_project')
django.setup()

# Import Django models
from cdb_app.models import ConcreteMix, MixComponent, PerformanceResult, MaterialType

# ## Data Extraction

# Get all mixes with 28-day strength results
def get_mixes_with_28d_strength():
    """Get all mixes with 28-day strength test results"""
    # Find performance results that are 28-day strength tests
    strength_results = PerformanceResult.objects.filter(
        age_days=28
    ).filter(
        category__icontains='compressive'
    ).union(
        PerformanceResult.objects.filter(age_days=28, category__icontains='strength')
    ).union(
        PerformanceResult.objects.filter(age_days=28, category__icontains='hardened')
    )
    
    # Get unique mix IDs
    mix_ids = strength_results.values_list('mix_id', flat=True).distinct()
    
    # Get the mixes
    mixes = ConcreteMix.objects.filter(pk__in=mix_ids)
    
    print(f"Found {mixes.count()} mixes with 28-day strength test results")
    return mixes, strength_results

# Get mix components by material type
def get_mix_components(mix_id):
    """Get components for a mix, organized by material type"""
    components = MixComponent.objects.filter(mix_id=mix_id)
    result = {}
    
    for comp in components:
        material_class = comp.material.material_class.class_code if comp.material.material_class else 'OTHER'
        if material_class not in result:
            result[material_class] = 0
        result[material_class] += comp.dosage_kg_m3 or 0
    
    return result

# ## Data Processing

def create_mix_dataframe(mixes, strength_results):
    """Create a DataFrame with mix data and 28-day strength results"""
    data = []
    
    for mix in mixes:
        # Get strength result for this mix
        mix_strength = strength_results.filter(mix_id=mix.id).order_by('-value_num').first()
        
        if not mix_strength:
            continue
            
        # Get components by material type
        components = get_mix_components(mix.id)
        
        # Create base record
        record = {
            'mix_id': mix.mix_id,
            'dataset': mix.dataset.dataset_name if mix.dataset else 'Unknown',
            'region': mix.region_country or 'Unknown',
            'w_c_ratio': mix.w_c_ratio,
            'w_b_ratio': mix.w_b_ratio,
            'strength_28d': mix_strength.value_num,
            'strength_unit': mix_strength.unit.unit_symbol if mix_strength.unit else 'MPa'
        }
        
        # Add component data
        for material_class, amount in components.items():
            record[f'{material_class}_kg_m3'] = amount
            
        data.append(record)
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Fill missing material amounts with 0
    material_columns = [col for col in df.columns if col.endswith('_kg_m3')]
    for col in material_columns:
        if col not in df.columns:
            df[col] = 0
        else:
            df[col].fillna(0, inplace=True)
    
    return df

# ## Visualization Functions

def plot_strength_distribution(df):
    """Plot the distribution of 28-day strength values"""
    plt.figure(figsize=(10, 6))
    sns.histplot(df['strength_28d'], kde=True)
    plt.title('Distribution of 28-day Strength Values')
    plt.xlabel('Strength (MPa)')
    plt.ylabel('Count')
    plt.grid(True, alpha=0.3)
    plt.show()

def plot_strength_vs_composition(df, component_col):
    """Plot strength vs a specific composition component"""
    plt.figure(figsize=(10, 6))
    sns.scatterplot(x=component_col, y='strength_28d', data=df, hue='dataset')
    plt.title(f'Strength vs {component_col}')
    plt.xlabel(f'{component_col} (kg/m³)')
    plt.ylabel('28-day Strength (MPa)')
    plt.grid(True, alpha=0.3)
    plt.show()
    
    # Calculate correlation
    corr = df[['strength_28d', component_col]].corr().iloc[0, 1]
    print(f"Correlation between 28-day strength and {component_col}: {corr:.3f}")

def plot_strength_vs_ratio(df, ratio_col):
    """Plot strength vs a specific ratio (w/c or w/b)"""
    if ratio_col not in df.columns:
        print(f"{ratio_col} not available in the data")
        return
        
    plt.figure(figsize=(10, 6))
    sns.scatterplot(x=ratio_col, y='strength_28d', data=df, hue='dataset')
    plt.title(f'Strength vs {ratio_col}')
    plt.xlabel(ratio_col)
    plt.ylabel('28-day Strength (MPa)')
    plt.grid(True, alpha=0.3)
    plt.show()
    
    # Show regression line
    plt.figure(figsize=(10, 6))
    sns.regplot(x=ratio_col, y='strength_28d', data=df)
    plt.title(f'Regression: Strength vs {ratio_col}')
    plt.xlabel(ratio_col)
    plt.ylabel('28-day Strength (MPa)')
    plt.grid(True, alpha=0.3)
    plt.show()
    
    # Calculate correlation
    corr = df[['strength_28d', ratio_col]].corr().iloc[0, 1]
    print(f"Correlation between 28-day strength and {ratio_col}: {corr:.3f}")

# ## Clustering Analysis

def prepare_data_for_clustering(df):
    """Prepare feature matrix for clustering"""
    # Select features (material compositions and ratios)
    feature_cols = [col for col in df.columns if col.endswith('_kg_m3') or col in ['w_c_ratio', 'w_b_ratio']]
    X = df[feature_cols].copy()
    
    # Handle missing values
    X.fillna(0, inplace=True)
    
    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    return X, X_scaled, feature_cols

def perform_clustering(X_scaled, n_clusters=4):
    """Perform K-means clustering"""
    # Determine optimal number of clusters using elbow method
    inertia = []
    K_range = range(2, min(10, len(X_scaled)))
    for k in K_range:
        kmeans = KMeans(n_clusters=k, random_state=42)
        kmeans.fit(X_scaled)
        inertia.append(kmeans.inertia_)
    
    # Plot elbow curve
    plt.figure(figsize=(10, 6))
    plt.plot(K_range, inertia, 'o-')
    plt.title('Elbow Method for Optimal k')
    plt.xlabel('Number of clusters (k)')
    plt.ylabel('Inertia')
    plt.grid(True, alpha=0.3)
    plt.show()
    
    # Perform clustering with chosen number of clusters
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    clusters = kmeans.fit_predict(X_scaled)
    
    return clusters, kmeans

def visualize_clusters(df, X, X_scaled, clusters, feature_cols, kmeans=None):
    """Visualize clusters in 2D using PCA or t-SNE"""
    # Add cluster labels to dataframe
    df_with_clusters = df.copy()
    df_with_clusters['cluster'] = clusters
    
    # Apply PCA for dimensionality reduction
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)
    
    # Create scatter plot of clusters
    plt.figure(figsize=(12, 8))
    scatter = plt.scatter(X_pca[:, 0], X_pca[:, 1], c=clusters, cmap='viridis', s=50, alpha=0.8)
    if kmeans is not None:
        centers = kmeans.cluster_centers_
        centers_pca = pca.transform(centers)
        plt.scatter(centers_pca[:, 0], centers_pca[:, 1], c='red', s=200, alpha=0.8, marker='X')
    plt.title('PCA Projection of Concrete Mix Clusters')
    plt.xlabel('Principal Component 1')
    plt.ylabel('Principal Component 2')
    plt.colorbar(scatter, label='Cluster')
    plt.grid(True, alpha=0.3)
    plt.show()
    
    # Create an interactive plot with Plotly
    df_plot = pd.DataFrame({
        'PC1': X_pca[:, 0],
        'PC2': X_pca[:, 1],
        'Cluster': clusters.astype(str),
        'Mix ID': df['mix_id'],
        'Strength': df['strength_28d'],
        'W/C Ratio': df['w_c_ratio']
    })
    
    fig = px.scatter(df_plot, x='PC1', y='PC2', color='Cluster', 
                    hover_data=['Mix ID', 'Strength', 'W/C Ratio'],
                    title='Interactive Cluster Visualization')
    fig.show()
    
    # Analyze clusters in terms of strength
    plt.figure(figsize=(10, 6))
    sns.boxplot(x='cluster', y='strength_28d', data=df_with_clusters)
    plt.title('Strength Distribution by Cluster')
    plt.xlabel('Cluster')
    plt.ylabel('28-day Strength (MPa)')
    plt.grid(True, alpha=0.3)
    plt.show()
    
    # Show cluster feature importances
    if kmeans is not None:
        importances = np.abs(kmeans.cluster_centers_)
        cluster_importances = pd.DataFrame(importances, columns=feature_cols)
        
        plt.figure(figsize=(14, 8))
        sns.heatmap(cluster_importances, annot=True, cmap='YlGnBu')
        plt.title('Feature Importance by Cluster')
        plt.show()
    
    return df_with_clusters

# ## Main Analysis

def main():
    print("Starting concrete mix strength classification analysis...")
    
    # Get data from database
    mixes, strength_results = get_mixes_with_28d_strength()
    
    # Create dataframe
    df = create_mix_dataframe(mixes, strength_results)
    print(f"Created dataframe with {len(df)} mixes")
    
    # Display basic statistics
    print("\nBasic Statistics:")
    print(df['strength_28d'].describe())
    
    # Plot strength distribution
    plot_strength_distribution(df)
    
    # Plot strength vs ratios
    plot_strength_vs_ratio(df, 'w_c_ratio')
    plot_strength_vs_ratio(df, 'w_b_ratio')
    
    # Plot strength vs key components (adjust based on available data)
    material_cols = [col for col in df.columns if col.endswith('_kg_m3')]
    for col in material_cols:
        plot_strength_vs_composition(df, col)
    
    # Prepare data for clustering
    X, X_scaled, feature_cols = prepare_data_for_clustering(df)
    
    # Perform clustering
    clusters, kmeans = perform_clustering(X_scaled, n_clusters=4)
    
    # Visualize clusters
    df_with_clusters = visualize_clusters(df, X, X_scaled, clusters, feature_cols, kmeans)
    
    print("\nCluster Analysis:")
    for cluster in sorted(df_with_clusters['cluster'].unique()):
        cluster_df = df_with_clusters[df_with_clusters['cluster'] == cluster]
        print(f"\nCluster {cluster} ({len(cluster_df)} mixes):")
        print(f"Average 28-day strength: {cluster_df['strength_28d'].mean():.2f} MPa")
        print(f"W/C ratio range: {cluster_df['w_c_ratio'].min():.2f} - {cluster_df['w_c_ratio'].max():.2f}")
        # Print top 3 most common materials in this cluster
        material_cols = [col for col in df.columns if col.endswith('_kg_m3')]
        avg_materials = cluster_df[material_cols].mean().sort_values(ascending=False)
        print("Top materials (avg kg/m³):")
        for mat, amount in avg_materials.head(3).items():
            if amount > 0:
                print(f"  {mat.replace('_kg_m3', '')}: {amount:.1f}")
    
    # Save results to CSV
    df_with_clusters.to_csv('strength_classification_results.csv', index=False)
    print("\nAnalysis complete. Results saved to 'strength_classification_results.csv'")
    
    return df_with_clusters

if __name__ == "__main__":
    main()
