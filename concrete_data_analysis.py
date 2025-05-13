import os
import sys
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.nonparametric.smoothers_lowess import lowess
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.linear_model import LinearRegression
import seaborn as sns
import django
from datetime import datetime

# Set up plotting style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.5)

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

# Import Django models
from django.db.models import Count, Q, F, Sum, Avg, Case, When, Value, FloatField
from cdb_app import models as cdb

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants
OUTPUT_DIR = 'analysis_output'
FIGURE_DPI = 300

# Create output directory if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def log_section(section_name):
    """Log a section header to make console output more readable."""
    logger.info(f"\n{'='*20} {section_name} {'='*20}\n")

def fetch_raw_data():
    """Fetch raw data from the database and create the initial dataframe."""
    log_section("Fetching Raw Data")
    
    # Get all concrete mixes with their components and 28-day strength results
    logger.info("Querying concrete mixes with components and 28-day strength results...")
    
    # First get all mixes
    mixes = list(cdb.ConcreteMix.objects.using('cdb').select_related('dataset').all())
    logger.info(f"Found {len(mixes)} total mixes in the database")
    
    # Prepare data structure for the dataframe
    mix_data = []
    
    for mix in mixes:
        # Basic mix data
        mix_dict = {
            'mix_id': mix.mix_id,
            'mix_code': mix.mix_code,
            'dataset': mix.dataset.dataset_name if mix.dataset else None,
            'w_c_ratio': mix.w_c_ratio,
            'w_b_ratio': mix.w_b_ratio,
        }
        
        # Get mix components
        components = cdb.MixComponent.objects.using('cdb').filter(mix=mix).select_related('material')
        
        # Initialize component-specific values
        mix_dict['cement_kg_m3'] = 0
        mix_dict['water_kg_m3'] = 0
        mix_dict['total_scm_kg_m3'] = 0
        mix_dict['total_coarse_agg_kg_m3'] = 0
        mix_dict['total_fine_agg_kg_m3'] = 0
        mix_dict['total_agg_kg_m3'] = 0
        
        # SCM details
        scm_components = []
        
        for comp in components:
            material_class = comp.material.material_class_id if comp.material else None
            dosage = comp.dosage_kg_m3 or 0
            
            if material_class == 'CEMENT':
                mix_dict['cement_kg_m3'] += dosage
            elif material_class == 'WATER':
                mix_dict['water_kg_m3'] += dosage
            elif material_class == 'SCM':
                mix_dict['total_scm_kg_m3'] += dosage
                scm_components.append({
                    'type': comp.material.subtype_code if comp.material else None,
                    'dosage': dosage
                })
            elif material_class == 'AGGR_C':
                mix_dict['total_coarse_agg_kg_m3'] += dosage
            elif material_class == 'AGGR_F':
                mix_dict['total_fine_agg_kg_m3'] += dosage
        
        # Aggregate all aggregates
        mix_dict['total_agg_kg_m3'] = mix_dict['total_coarse_agg_kg_m3'] + mix_dict['total_fine_agg_kg_m3']
        
        # Store raw SCM information
        if scm_components:
            # Sort by dosage (highest first) to identify the primary SCM
            scm_components.sort(key=lambda x: x['dosage'], reverse=True)
            mix_dict['scm_raw_type'] = ', '.join([f"{comp['type']}:{comp['dosage']}" for comp in scm_components])
            mix_dict['scm_primary_raw'] = scm_components[0]['type'] if scm_components else None
        else:
            mix_dict['scm_raw_type'] = 'None'
            mix_dict['scm_primary_raw'] = 'None'
        
        # Get performance results (28-day compressive strength)
        results = cdb.PerformanceResult.objects.using('cdb').filter(
            mix=mix, category='hardened', age_days=28
        ).order_by('age_days')
        
        if results.exists():
            # Use the first 28-day strength result
            mix_dict['compressive_strength_28d_mpa'] = results.first().value_num
        else:
            mix_dict['compressive_strength_28d_mpa'] = None
        
        # Add to the dataset
        mix_data.append(mix_dict)
    
    # Create dataframe
    df = pd.DataFrame(mix_data)
    
    # Log statistics
    logger.info(f"Created initial dataframe with {len(df)} rows")
    logger.info(f"Mixes with 28-day strength: {df['compressive_strength_28d_mpa'].notna().sum()}")
    
    return df

def standardize_scm_types(df):
    """Standardize SCM types to canonical labels."""
    log_section("Standardizing SCM Types")
    
    # Create a standardization mapping
    scm_mapping = {
        # Fly Ash variants
        'FA': 'Fly Ash',
        'fa': 'Fly Ash',
        'cfa': 'Fly Ash',
        'fly_ash_bituminous_coal': 'Fly Ash',
        'fly_ash_lignite_brown_coal_': 'Fly Ash',
        
        # Silica Fume variants
        'SF': 'Silica Fume',
        'sf': 'Silica Fume',
        
        # GGBS variants
        'BFS': 'GGBS',
        'ggbfs': 'GGBS',
        'GGBFS': 'GGBS',
        'ggbfs': 'GGBS',
        'Blast Furnace Slag': 'GGBS',
        
        # Limestone powder variants
        'Limestone Powder': 'Limestone Powder',
        'cc': 'Limestone Powder', 
        
        # Natural pozzolan
        'natural_pozzolan': 'Natural Pozzolan',
        
        # None or empty
        'None': 'None',
        'none': 'None',
        '': 'None',
        '-': 'None',
        
        # Others remain as is but will be caught by the default case
    }
    
    # Function to map SCM raw type to standardized type
    def map_scm_type(raw_type):
        if pd.isna(raw_type) or raw_type is None:
            return 'None'
        
        # Check if the raw type directly matches a key in mapping
        if raw_type in scm_mapping:
            return scm_mapping[raw_type]
        
        # Check for substring matches in the raw type
        for key, value in scm_mapping.items():
            if key.lower() in raw_type.lower() or value.lower() in raw_type.lower():
                return value
        
        # If no match, return the original as is
        return raw_type
    
    # Apply the mapping to create standardized SCM type column
    df['scm_primary_type'] = df['scm_primary_raw'].apply(map_scm_type)
    
    # Log counts of each SCM type before and after standardization
    logger.info("SCM types before standardization:")
    logger.info(df['scm_primary_raw'].value_counts().to_string())
    
    logger.info("\nSCM types after standardization:")
    logger.info(df['scm_primary_type'].value_counts().to_string())
    
    return df

def calculate_derived_variables(df):
    """Calculate derived variables for analysis."""
    log_section("Calculating Derived Variables")
    
    # Calculate binder content (cement + SCM)
    df['binder_content_kg_m3'] = df['cement_kg_m3'] + df['total_scm_kg_m3']
    
    # Calculate SCM replacement percentage - safely handle division by zero
    # Convert pandas Series to numpy arrays for safe division
    total_scm = df['total_scm_kg_m3'].values
    binder_content = df['binder_content_kg_m3'].values
    
    with np.errstate(divide='ignore', invalid='ignore'):
        # Create result array initialized with NaN
        scm_repl_pct = np.full_like(binder_content, np.nan, dtype=float)
        # Only calculate percentage where denominator > 0
        mask = binder_content > 0
        scm_repl_pct[mask] = 100 * total_scm[mask] / binder_content[mask]
        
        # Assign back to dataframe
        df['scm_replacement_pct'] = scm_repl_pct
    
    # Calculate fine-to-coarse ratio - safely handle division by zero
    # Convert pandas Series to numpy arrays for safe division
    fine_agg = df['total_fine_agg_kg_m3'].values
    coarse_agg = df['total_coarse_agg_kg_m3'].values
    
    with np.errstate(divide='ignore', invalid='ignore'):
        # Create result array initialized with NaN
        f_c_ratio = np.full_like(fine_agg, np.nan, dtype=float)
        # Only calculate ratio where denominator > 0
        mask = coarse_agg > 0
        f_c_ratio[mask] = fine_agg[mask] / coarse_agg[mask]
        
        # Assign back to dataframe
        df['fine_to_coarse_ratio'] = f_c_ratio
    
    # Calculate binder-to-aggregate ratio - safely handle division by zero
    # Convert pandas Series to numpy arrays for safe division
    binder_content = df['binder_content_kg_m3'].values
    total_agg = df['total_agg_kg_m3'].values
    
    with np.errstate(divide='ignore', invalid='ignore'):
        # Create result array initialized with NaN
        b_a_ratio = np.full_like(binder_content, np.nan, dtype=float)
        # Only calculate ratio where denominator > 0
        mask = total_agg > 0
        b_a_ratio[mask] = binder_content[mask] / total_agg[mask]
        
        # Assign back to dataframe
        df['binder_to_aggregate_ratio'] = b_a_ratio
    
    # Log statistics on newly calculated columns
    for col in ['binder_content_kg_m3', 'scm_replacement_pct', 'fine_to_coarse_ratio', 'binder_to_aggregate_ratio']:
        valid_count = df[col].notna().sum()
        logger.info(f"{col}: {valid_count} valid values ({valid_count/len(df)*100:.1f}%)")
    
    return df

def create_minimal_tidy_dataset(df):
    """Create a minimal tidy dataset with selected columns."""
    log_section("Creating Minimal Tidy Dataset")
    
    # Select required columns
    tidy_cols = [
        'dataset', 'mix_id', 'mix_code', 'scm_primary_type',
        'cement_kg_m3', 'binder_content_kg_m3', 'scm_replacement_pct',
        'w_c_ratio', 'w_b_ratio', 'water_kg_m3',
        'compressive_strength_28d_mpa',
        'total_coarse_agg_kg_m3', 'total_fine_agg_kg_m3', 'total_agg_kg_m3',
        'fine_to_coarse_ratio', 'binder_to_aggregate_ratio'
    ]
    
    # Create tidy dataframe with only the needed columns
    df_tidy = df[tidy_cols].copy()
    
    # Convert all Decimal objects to float to avoid visualization issues
    numeric_cols = df_tidy.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        df_tidy[col] = df_tidy[col].astype(float)
    
    # Filter to include only mixes with 28-day strength results
    df_tidy_with_strength = df_tidy[df_tidy['compressive_strength_28d_mpa'].notna()].copy()
    
    # Log statistics
    logger.info(f"Complete tidy dataset: {len(df_tidy)} mixes")
    logger.info(f"Tidy dataset with 28-day strength: {len(df_tidy_with_strength)} mixes")
    logger.info(f"Tidy dataset with w/c ratio: {df_tidy_with_strength['w_c_ratio'].notna().sum()} mixes")
    logger.info(f"Tidy dataset with w/b ratio: {df_tidy_with_strength['w_b_ratio'].notna().sum()} mixes")
    
    # Save the complete tidy dataset
    tidy_path = os.path.join(OUTPUT_DIR, 'cleaned_mixes.csv')
    pkl_path = os.path.join(OUTPUT_DIR, 'cleaned_mixes.pkl')
    
    df_tidy.to_csv(tidy_path, index=False, encoding='utf-8')
    with open(pkl_path, 'wb') as f:
        pickle.dump(df_tidy, f)
    
    logger.info(f"Saved tidy dataset to {tidy_path} and {pkl_path}")
    
    return df_tidy, df_tidy_with_strength

def create_visualizations(df):
    """Create exploratory visualizations."""
    log_section("Creating Exploratory Visualizations")
    
    # Filter to mixes with strength data
    df_viz = df[df['compressive_strength_28d_mpa'].notna()].copy()
    
    # Explicitly convert all numeric columns to float
    numeric_cols = df_viz.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        df_viz[col] = df_viz[col].astype(float)
    
    # 1. Strength vs w/c ratio by SCM type
    logger.info("Creating 'strength_vs_wc_by_scm.png'...")
    plt.figure(figsize=(12, 8))
    
    # Filter for mixes with w/c ratio
    df_wc = df_viz[df_viz['w_c_ratio'].notna()].copy()
    
    # Get top 5 SCM types by frequency for clarity in the plot
    top_scm_types = df_wc['scm_primary_type'].value_counts().head(5).index.tolist()
    df_wc_filtered = df_wc[df_wc['scm_primary_type'].isin(top_scm_types)]
    
    # Create scatter plot
    scatter = sns.scatterplot(
        data=df_wc_filtered, 
        x='w_c_ratio', 
        y='compressive_strength_28d_mpa',
        hue='scm_primary_type',
        alpha=0.6,
        s=70
    )
    
    # Add LOWESS trend lines for each SCM type
    for scm_type in top_scm_types:
        temp_df = df_wc_filtered[df_wc_filtered['scm_primary_type'] == scm_type]
        if len(temp_df) > 5:  # Only add trend if we have enough points
            trend = lowess(
                temp_df['compressive_strength_28d_mpa'],
                temp_df['w_c_ratio'],
                frac=0.6,
                it=1
            )
            plt.plot(trend[:, 0], trend[:, 1], linewidth=2.5)
    
    plt.title('28-Day Compressive Strength vs. Water-Cement Ratio by SCM Type')
    plt.xlabel('Water-Cement Ratio (w/c)')
    plt.ylabel('28-Day Compressive Strength (MPa)')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'strength_vs_wc_by_scm.png'), dpi=FIGURE_DPI)
    plt.close()
    
    # 2. Strength vs binder content
    logger.info("Creating 'strength_vs_binder_content.png'...")
    plt.figure(figsize=(12, 8))
    
    # Create scatter plot
    g = sns.scatterplot(
        data=df_viz, 
        x='binder_content_kg_m3', 
        y='compressive_strength_28d_mpa',
        hue='scm_primary_type',
        alpha=0.6,
        s=70
    )
    
    # Calculate Pearson correlation coefficient for each SCM type
    correlations = {}
    for scm_type in df_viz['scm_primary_type'].unique():
        temp_df = df_viz[df_viz['scm_primary_type'] == scm_type]
        if len(temp_df) > 5:
            corr = temp_df[['binder_content_kg_m3', 'compressive_strength_28d_mpa']].corr().iloc[0, 1]
            correlations[scm_type] = corr
    
    # Update legend with correlation coefficients
    handles, labels = g.get_legend_handles_labels()
    new_labels = []
    for label in labels:
        if label in correlations:
            new_labels.append(f"{label} (r={correlations[label]:.2f})")
        else:
            new_labels.append(label)
    
    plt.legend(handles=handles, labels=new_labels, title='SCM Type (Pearson r)')
    plt.title('28-Day Compressive Strength vs. Total Binder Content by SCM Type')
    plt.xlabel('Total Binder Content (kg/m³)')
    plt.ylabel('28-Day Compressive Strength (MPa)')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'strength_vs_binder_content.png'), dpi=FIGURE_DPI)
    plt.close()
    
    # 3. Strength vs SCM replacement percentage
    logger.info("Creating 'strength_vs_scm_replacement.png'...")
    plt.figure(figsize=(12, 8))
    
    # Filter for mixes with SCM replacement and exclude 'None' SCM type
    df_scm = df_viz[(df_viz['scm_replacement_pct'].notna()) & 
                  (df_viz['scm_primary_type'] != 'None')].copy()
    
    # Ensure all numeric columns in this filtered dataframe are float
    numeric_cols = df_scm.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        df_scm[col] = df_scm[col].astype(float)
    
    # Manually convert the specific columns we're plotting to ensure they're float
    df_scm['scm_replacement_pct'] = df_scm['scm_replacement_pct'].astype(float)
    df_scm['compressive_strength_28d_mpa'] = df_scm['compressive_strength_28d_mpa'].astype(float)
    
    # Create scatter plot
    sns.scatterplot(
        data=df_scm, 
        x='scm_replacement_pct', 
        y='compressive_strength_28d_mpa',
        hue='scm_primary_type',
        alpha=0.6,
        s=70
    )
    
    # Add overall trend line using direct numpy array instead of DataFrame
    try:
        # Get data as numpy arrays
        x = df_scm['scm_replacement_pct'].values
        y = df_scm['compressive_strength_28d_mpa'].values
        
        # Add trendline using numpy polyfit instead of regplot
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        plt.plot(x, p(x), 'k--', linewidth=2)
    except Exception as e:
        logger.warning(f"Could not add trendline: {e}")
        # Just skip the trendline if it fails
    
    plt.title('28-Day Compressive Strength vs. SCM Replacement Percentage')
    plt.xlabel('SCM Replacement (% of total binder)')
    plt.ylabel('28-Day Compressive Strength (MPa)')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'strength_vs_scm_replacement.png'), dpi=FIGURE_DPI)
    plt.close()
    
    # 4. Strength distribution by dataset
    logger.info("Creating 'strength_distribution_by_dataset.png'...")
    plt.figure(figsize=(12, 8))
    
    # Create box plot
    sns.boxplot(
        data=df_viz, 
        x='dataset', 
        y='compressive_strength_28d_mpa',
        palette='viridis'
    )
    
    # Add individual points (swarmplot or stripplot)
    sns.stripplot(
        data=df_viz, 
        x='dataset', 
        y='compressive_strength_28d_mpa',
        color='black',
        alpha=0.3,
        size=3,
        jitter=True
    )
    
    plt.title('Distribution of 28-Day Compressive Strength by Dataset')
    plt.xlabel('Dataset')
    plt.ylabel('28-Day Compressive Strength (MPa)')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'strength_distribution_by_dataset.png'), dpi=FIGURE_DPI)
    plt.close()
    
    logger.info("All visualizations created successfully")

def build_abrams_models(df):
    """Build Abrams' Law models (strength vs w/c ratio)."""
    log_section("Building Abrams' Law Models")
    
    # Filter to mixes with both strength and w/c ratio
    df_abrams = df[(df['compressive_strength_28d_mpa'].notna()) & 
                  (df['w_c_ratio'].notna())].copy()
    
    # Ensure all numeric columns are float
    df_abrams['compressive_strength_28d_mpa'] = pd.to_numeric(df_abrams['compressive_strength_28d_mpa'], errors='coerce')
    df_abrams['w_c_ratio'] = pd.to_numeric(df_abrams['w_c_ratio'], errors='coerce')
    
    # Drop any rows with NaN after conversion
    df_abrams = df_abrams.dropna(subset=['compressive_strength_28d_mpa', 'w_c_ratio'])
    
    # Initialize results dataframe
    abrams_results = []
    
    # Model for all mixes
    logger.info(f"Building Abrams model for all mixes (n={len(df_abrams)})")
    X = df_abrams[['w_c_ratio']].astype(float)
    y = df_abrams['compressive_strength_28d_mpa'].astype(float)
    
    # Add constant for intercept
    X_with_const = sm.add_constant(X)
    
    # Verify data types
    logger.info(f"X data type: {X.dtypes}")
    logger.info(f"y data type: {y.dtype}")
    
    # Fit model
    try:
        model = sm.OLS(y, X_with_const).fit()
        
        # Calculate metrics
        predictions = model.predict(X_with_const)
        r2 = r2_score(y, predictions)
        rmse = np.sqrt(mean_squared_error(y, predictions))
        
        # Add to results
        abrams_results.append({
            'group': 'All Mixes',
            'sample_size': len(df_abrams),
            'intercept': model.params['const'],
            'w_c_coef': model.params['w_c_ratio'],
            'r_squared': r2,
            'rmse': rmse
        })
    except Exception as e:
        logger.error(f"Error building overall Abrams model: {e}")
        # Add placeholder with error info
        abrams_results.append({
            'group': 'All Mixes',
            'sample_size': len(df_abrams),
            'intercept': np.nan,
            'w_c_coef': np.nan,
            'r_squared': np.nan,
            'rmse': np.nan,
            'error': str(e)
        })
    
    # Models for each SCM type
    for scm_type in df_abrams['scm_primary_type'].unique():
        temp_df = df_abrams[df_abrams['scm_primary_type'] == scm_type]
        
        # Only build model if we have enough samples
        if len(temp_df) >= 10:
            logger.info(f"Building Abrams model for {scm_type} (n={len(temp_df)})")
            try:
                # Convert to numeric just to be safe
                X = temp_df[['w_c_ratio']].astype(float)
                y = temp_df['compressive_strength_28d_mpa'].astype(float)
                
                X_with_const = sm.add_constant(X)
                model = sm.OLS(y, X_with_const).fit()
                
                predictions = model.predict(X_with_const)
                r2 = r2_score(y, predictions)
                rmse = np.sqrt(mean_squared_error(y, predictions))
                
                abrams_results.append({
                    'group': scm_type,
                    'sample_size': len(temp_df),
                    'intercept': model.params['const'],
                    'w_c_coef': model.params['w_c_ratio'],
                    'r_squared': r2,
                    'rmse': rmse
                })
            except Exception as e:
                logger.warning(f"Error building Abrams model for {scm_type}: {e}")
                # Add placeholder with error info
                abrams_results.append({
                    'group': scm_type,
                    'sample_size': len(temp_df),
                    'intercept': np.nan,
                    'w_c_coef': np.nan,
                    'r_squared': np.nan,
                    'rmse': np.nan,
                    'error': str(e)
                })
    
    # Create results dataframe
    df_abrams_results = pd.DataFrame(abrams_results)
    
    # Save results
    abrams_path = os.path.join(OUTPUT_DIR, 'abrams_models.csv')
    df_abrams_results.to_csv(abrams_path, index=False, encoding='utf-8')
    
    logger.info(f"Saved Abrams model results to {abrams_path}")
    logger.info("Abrams model results summary:")
    logger.info(df_abrams_results.to_string(index=False))
    
    return df_abrams_results

def build_multivariate_model(df):
    """Build multivariate OLS model for strength prediction."""
    log_section("Building Multivariate Baseline Model")
    
    # Filter to mixes with required variables
    required_vars = ['compressive_strength_28d_mpa', 'w_c_ratio', 'scm_replacement_pct', 'binder_content_kg_m3']
    df_model = df[df[required_vars].notna().all(axis=1)].copy()
    
    # Convert all numeric columns to float
    numeric_cols = df_model.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        df_model[col] = pd.to_numeric(df_model[col], errors='coerce')
    
    # Drop any rows with NaN after conversion
    df_model = df_model.dropna(subset=required_vars)
    
    # Create dummy variables for SCM types - dropping the first to avoid multicollinearity
    df_with_dummies = pd.get_dummies(df_model, columns=['scm_primary_type'], prefix='scm_type', drop_first=True)
    
    # Check sample size
    if len(df_model) < 100:
        logger.warning(f"Small sample size for multivariate model: {len(df_model)} observations")
    else:
        logger.info(f"Building multivariate model with {len(df_model)} observations")
    
    try:
        # Directly use the array-based interface instead of the formula interface
        # Extract dependent variable (y)
        y = df_with_dummies['compressive_strength_28d_mpa'].astype(float)
        
        # Select predictor columns (X)
        predictor_vars = ['w_c_ratio', 'scm_replacement_pct', 'binder_content_kg_m3']
        scm_dummy_cols = [col for col in df_with_dummies.columns if col.startswith('scm_type_')]
        all_predictors = predictor_vars + scm_dummy_cols
        
        # Extract features and convert to float
        X = df_with_dummies[all_predictors].astype(float)
        
        # Log the model specifics
        logger.info(f"Dependent variable: compressive_strength_28d_mpa")
        logger.info(f"Predictors: {', '.join(all_predictors)}")
        logger.info(f"Number of SCM dummy variables: {len(scm_dummy_cols)}")
        
        # Add constant for intercept
        X_with_const = sm.add_constant(X)
        
        # Fit the model using the arrays directly
        model = sm.OLS(y, X_with_const).fit()
        
        # Save model summary
        summary_path = os.path.join(OUTPUT_DIR, 'ols_baseline.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(str(model.summary()))
        
        # Save pickled model
        model_path = os.path.join(OUTPUT_DIR, 'ols_baseline_model.pkl')
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        logger.info(f"Saved multivariate model summary to {summary_path}")
        logger.info(f"Saved pickled model to {model_path}")
        
        # Log key metrics
        logger.info(f"Model R-squared: {model.rsquared:.4f}")
        logger.info(f"Model Adj. R-squared: {model.rsquared_adj:.4f}")
        
        return model
    
    except Exception as e:
        logger.error(f"Error building multivariate model: {e}")
        return None

def main():
    """Main function to run the complete analysis pipeline."""
    start_time = datetime.now()
    log_section("CONCRETE MIX DATABASE ANALYSIS")
    logger.info(f"Analysis started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. Data Preparation
        raw_df = fetch_raw_data()
        
        # 2. Data Cleaning & Standardization
        df_standardized = standardize_scm_types(raw_df)
        df_with_derived = calculate_derived_variables(df_standardized)
        df_tidy, df_tidy_with_strength = create_minimal_tidy_dataset(df_with_derived)
        
        # 3. Exploratory Visualizations
        create_visualizations(df_tidy_with_strength)
        
        # 4. Baseline Modeling
        abrams_results = build_abrams_models(df_tidy_with_strength)
        multivariate_model = build_multivariate_model(df_tidy_with_strength)
        
        # Calculate processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Final log of all generated files
        log_section("ANALYSIS COMPLETE")
        logger.info(f"Analysis completed in {processing_time:.1f} seconds")
        logger.info("\nGenerated files:")
        
        for filename in os.listdir(OUTPUT_DIR):
            file_path = os.path.join(OUTPUT_DIR, filename)
            file_size = os.path.getsize(file_path) / 1024  # Size in KB
            logger.info(f"- {filename} ({file_size:.1f} KB)")
        
        return df_tidy, abrams_results, multivariate_model
    
    except Exception as e:
        logger.error(f"Error in analysis pipeline: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    main()
