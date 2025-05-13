import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

# Import Django models
from django.db.models import Count, Q, F, Sum, Avg, Min, Max
from cdb_app import models as cdb

def analyze_datasets_strength():
    """Analyze datasets and their strength coverage."""
    print("\n1. Analyzing datasets and their strength coverage...")
    try:
        ds_strength = (
            cdb.ConcreteMix.objects.using('cdb')
              .values(name=F('dataset__dataset_name'))
              .annotate(
                  mixes=Count('mix_id', distinct=True),
                  mixes_with_cs_28=Count(
                      'mix_id',
                      filter=Q(performance_results__category='hardened',
                               performance_results__age_days=28,
                               performance_results__value_num__isnull=False),
                      distinct=True)
              )
              .order_by('name')
        )
        df_ds = pd.DataFrame(list(ds_strength))
        
        # Calculate percentage coverage
        df_ds['coverage_pct'] = (df_ds['mixes_with_cs_28'] / df_ds['mixes'] * 100).round(1)
        
        print("\nDatasets vs Strength Coverage:")
        print(df_ds.to_string(index=False))
        return df_ds
    except Exception as e:
        print(f"Error analyzing datasets: {e}")
        return pd.DataFrame()

def analyze_scm_catalog():
    """Analyze supplementary cementitious materials (SCM) usage."""
    print("\n2. Analyzing SCM catalog...")
    try:
        scm_qs = (
            cdb.MixComponent.objects.using('cdb')
              .filter(material__material_class_id='SCM')
              .values(scm=F('material__subtype_code'))
              .annotate(mix_count=Count('mix_id', distinct=True))
              .order_by('-mix_count')
        )
        df_scm = pd.DataFrame(list(scm_qs))
        
        print("\nSCM Counts:")
        print(df_scm.to_string(index=False))
        
        # Get total number of mixes that contain SCMs
        total_scm_mixes = cdb.MixComponent.objects.using('cdb').filter(
            material__material_class_id='SCM'
        ).values('mix_id').distinct().count()
        print(f"Total mixes containing SCMs: {total_scm_mixes}")
        
        # Save SCM counts for later use
        df_scm.to_csv('scm_counts.csv', index=False)
        print("Saved SCM counts \u2192 scm_counts.csv")
        return df_scm
    except Exception as e:
        print(f"Error analyzing SCM catalog: {e}")
        return pd.DataFrame()

def analyze_column_completeness():
    """Analyze completeness of numeric columns in ConcreteMix."""
    print("\n3. Analyzing column completeness...")
    try:
        # Check model fields first to verify they exist
        model_fields = [field.name for field in cdb.ConcreteMix._meta.get_fields()]
        print(f"Available fields in ConcreteMix model: {', '.join(model_fields)}")
        
        # Define columns to check based on the model fields
        NUM_COLS = ['w_c_ratio', 'w_b_ratio', 'target_slump_mm', 'strength_class']
        completeness = []
        total_mixes = cdb.ConcreteMix.objects.using('cdb').count()
        
        for col in NUM_COLS:
            try:
                non_null_count = cdb.ConcreteMix.objects.using('cdb').filter(**{f'{col}__isnull': False}).count()
                completeness.append({
                    'column': col,
                    'non_null': non_null_count,
                    'total': total_mixes,
                    'coverage_pct': round((non_null_count / total_mixes) * 100, 1) if total_mixes > 0 else 0
                })
            except Exception as col_error:
                print(f"Warning: Error checking column {col}: {col_error}")
        
        df_complete = pd.DataFrame(completeness)
        print("\nColumn Completeness:")
        print(df_complete.to_string(index=False))
        return df_complete
    except Exception as e:
        print(f"Error analyzing column completeness: {e}")
        return pd.DataFrame()

def plot_scm_usage(df_scm):
    """Create a bar plot showing SCM usage."""
    print("\n4. Creating SCM usage plot...")
    try:
        if not df_scm.empty:
            plt.figure(figsize=(10, 6))
            ax = df_scm.plot(kind='bar', x='scm', y='mix_count', legend=False, color='skyblue')
            plt.ylabel('Number of mixes')
            plt.xlabel('SCM type')
            plt.title('SCM usage across DS1–DS6')
            plt.xticks(rotation=45, ha='right')
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Add data labels on top of each bar
            for i, v in enumerate(df_scm['mix_count']):
                ax.text(i, v + 5, str(v), ha='center')
                
            plt.tight_layout()
            plt.savefig('scm_usage.png')
            print("SCM usage plot saved to scm_usage.png")
    except Exception as e:
        print(f"Error creating SCM usage plot: {e}")

def analyze_material_classes():
    """Analyze material classes used across datasets."""
    print("\n5. Analyzing material classes...")
    try:
        material_classes = (
            cdb.MixComponent.objects.using('cdb')
              .values(class_code=F('material__material_class_id'))
              .annotate(mix_count=Count('mix_id', distinct=True))
              .order_by('-mix_count')
        )
        df_classes = pd.DataFrame(list(material_classes))
        print("\nMaterial Classes:")
        print(df_classes.to_string(index=False))
        
        # Add dataset breakdown for each material class
        print("\nMaterial class usage by dataset:")
        for class_code in df_classes['class_code'].unique():
            dataset_counts = (
                cdb.MixComponent.objects.using('cdb')
                .filter(material__material_class_id=class_code)
                .values(dataset=F('mix__dataset__dataset_name'))
                .annotate(mix_count=Count('mix_id', distinct=True))
                .order_by('dataset')
            )
            if dataset_counts:
                df_dataset = pd.DataFrame(list(dataset_counts))
                print(f"\n{class_code} usage by dataset:")
                print(df_dataset.to_string(index=False))
                
        return df_classes
    except Exception as e:
        print(f"Error analyzing material classes: {e}")
        return pd.DataFrame()

def analyze_strength_stats():
    """Analyze compressive strength statistics by dataset."""
    print("\n6. Analyzing compressive strength statistics...")
    try:
        strength_stats = (
            cdb.PerformanceResult.objects.using('cdb')
              .filter(category='hardened', age_days=28)
              .values(dataset=F('mix__dataset__dataset_name'))
              .annotate(
                  count=Count('result_id'),
                  avg_strength=Avg('value_num'),
                  min_strength=Min('value_num'),
                  max_strength=Max('value_num')
              )
              .order_by('dataset')
        )
        df_strength = pd.DataFrame(list(strength_stats))
        if not df_strength.empty:
            for col in ['avg_strength', 'min_strength', 'max_strength']:
                if col in df_strength.columns:
                    df_strength[col] = df_strength[col].round(2)
                    
        print("\nCompressive Strength Statistics (28-day):")
        print(df_strength.to_string(index=False))
        return df_strength
    except Exception as e:
        print(f"Error analyzing strength statistics: {e}")
        return pd.DataFrame()

def main():
    print("==== Concrete Mix Database Analysis ====")
    print("Analyzing CDB database containing DS1-DS6 datasets")
    
    # Run all analyses
    df_ds = analyze_datasets_strength()
    df_scm = analyze_scm_catalog()
    df_complete = analyze_column_completeness()
    df_classes = analyze_material_classes()
    df_strength = analyze_strength_stats()
    
    # Create plot
    plot_scm_usage(df_scm)
    
    print("\n==== Analysis Complete ====")
    print("Summary:")
    print(f"- Total datasets: {len(df_ds)}")
    if not df_ds.empty:
        total_mixes = df_ds['mixes'].sum()
        total_with_strength = df_ds['mixes_with_cs_28'].sum()
        print(f"- Total mixes: {total_mixes}")
        print(f"- Mixes with 28-day strength: {total_with_strength} ({round(total_with_strength/total_mixes*100, 1)}%)")
    if not df_scm.empty:
        print(f"- Unique SCM types: {len(df_scm)}")
    print("\nFiles saved:")
    print("- scm_counts.csv")
    print("- scm_usage.png")

if __name__ == "__main__":
    main()
