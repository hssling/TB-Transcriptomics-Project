import pandas as pd

df = pd.read_csv('outputs/interpretation/treatment_normalization_analysis.csv')

print('='*80)
print('TREATMENT NORMALIZATION ANALYSIS RESULTS')
print('='*80)

print('\nAll genes analyzed:')
print(df[['gene', 'baseline_direction', 'baseline_fold_change', 'treatment_change', 'normalization_percent', 'normalized', 'p_value']].to_string(index=False))

print('\n' + '='*80)
print('SUMMARY')
print('='*80)
print(f'Total genes: {len(df)}')
print(f'Fully normalized (>50%): {len(df[df["normalized"]=="YES"])} ({len(df[df["normalized"]=="YES"])/len(df)*100:.1f}%)')
print(f'Statistically significant (p<0.05): {len(df[df["p_value"]<0.05])} ({len(df[df["p_value"]<0.05])/len(df)*100:.1f}%)')

# Expected direction
up_decreased = len(df[(df['baseline_direction']=='UP') & (df['treatment_change']<0)])
down_increased = len(df[(df['baseline_direction']=='DOWN') & (df['treatment_change']>0)])
total_expected = up_decreased + down_increased

print(f'Genes changing in expected direction: {total_expected}/{len(df)} ({total_expected/len(df)*100:.1f}%)')
print(f'  - Upregulated genes that decreased: {up_decreased}')
print(f'  - Downregulated genes that increased: {down_increased}')
