#!/usr/bin/env python3
import os
import re
from collections import defaultdict
from datetime import datetime

# Read branch activity data
branches = []
with open('branches_activity.tsv', 'r') as f:
    header = f.readline()
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) >= 6:
            branches.append({
                'name': parts[0],
                'last_date': parts[1],
                'commits_8d': int(parts[2]),
                'ahead': int(parts[3]),
                'behind': int(parts[4]),
                'unmerged': int(parts[5])
            })

# Separate branches by status
merged_main = [b for b in branches if b['name'] == 'main']
unmerged_branches = [b for b in branches if b['unmerged'] > 0 and b['name'] not in ['main', 'origin']]
wip_branches = [b for b in branches if b['unmerged'] == 0 and b['name'] not in ['main', 'origin']]

# Sort unmerged by commit count
unmerged_branches.sort(key=lambda x: x['unmerged'], reverse=True)

# Categorize branches
feature_branches = []
fix_branches = []
impl_branches = []
integrate_branches = []
pilot_branches = []

for b in unmerged_branches:
    name = b['name']
    if name.startswith('feat/TC-'):
        feature_branches.append(b)
    elif name.startswith('fix/'):
        fix_branches.append(b)
    elif name.startswith('impl/'):
        impl_branches.append(b)
    elif name.startswith('integrate/'):
        integrate_branches.append(b)
    elif 'pilot' in name or 'golden' in name:
        pilot_branches.append(b)

# Read commits on main
main_commits = []
if os.path.exists('branch_main_commits_8d.txt'):
    with open('branch_main_commits_8d.txt', 'r') as f:
        main_commits = [line.strip() for line in f if line.strip()]

print("=" * 80)
print("GIT WORK SUMMARY - LAST 8 DAYS")
print("=" * 80)
print()

print("## 1. MERGED INTO MAIN")
print()
if main_commits:
    for commit in main_commits:
        print(f"- {commit}")
else:
    print("- No commits on main in last 8 days")
print()

print("## 2. NOT YET MERGED (Branches with Work to Merge)")
print()

# Group by category
print("### Core Task Cards (TC-xxx Feature Branches)")
print()
for b in feature_branches[:15]:  # Top 15
    safe_name = b['name'].replace('/', '_').replace('origin_', '')
    
    # Read diffstat to get key files
    diffstat_file = f"branch_{safe_name}_diffstat.txt"
    key_areas = set()
    if os.path.exists(diffstat_file):
        with open(diffstat_file, 'r') as f:
            lines = f.readlines()
            for line in lines[:10]:  # Top 10 files
                if '|' in line:
                    filepath = line.split('|')[0].strip()
                    if filepath:
                        # Extract key directory
                        parts = filepath.split('/')
                        if len(parts) > 1:
                            key_areas.add(parts[0])
    
    areas_str = ', '.join(sorted(list(key_areas))[:3]) if key_areas else "various"
    tc_num = b['name'].split('TC-')[1].split('-')[0] if 'TC-' in b['name'] else "?"
    
    print(f"- **{b['name']}**: {b['unmerged']} unmerged commits (TC-{tc_num}, touches: {areas_str})")

if len(feature_branches) > 15:
    print(f"- ... and {len(feature_branches) - 15} more TC feature branches")
print()

if pilot_branches:
    print("### Pilot/Golden Path Branches")
    print()
    for b in pilot_branches:
        safe_name = b['name'].replace('/', '_').replace('origin_', '')
        print(f"- **{b['name']}**: {b['unmerged']} unmerged commits (last: {b['last_date'][:10]})")
    print()

if fix_branches:
    print("### Fix Branches")
    print()
    for b in fix_branches:
        print(f"- **{b['name']}**: {b['unmerged']} unmerged commits (last: {b['last_date'][:10]})")
    print()

if impl_branches:
    print("### Implementation Branches")
    print()
    for b in impl_branches:
        print(f"- **{b['name']}**: {b['unmerged']} unmerged commits (last: {b['last_date'][:10]})")
    print()

if integrate_branches:
    print("### Integration Branches")
    print()
    for b in integrate_branches:
        print(f"- **{b['name']}**: {b['unmerged']} unmerged commits (last: {b['last_date'][:10]})")
    print()

print("## 3. WIP / STALLED BRANCHES")
print()
if wip_branches:
    for b in wip_branches:
        if b['name'] not in ['main', 'origin']:
            print(f"- **{b['name']}**: {b['commits_8d']} commits in last 8 days (all merged)")
else:
    print("- No stalled branches detected")
print()

print("## 4. RISKS / CONFLICTS / NOTES")
print()
print(f"- **Total branches with unmerged work**: {len(unmerged_branches)}")
print(f"- **Total unmerged commits across all branches**: {sum(b['unmerged'] for b in unmerged_branches)}")
print(f"- **Working tree is dirty**: Yes (untracked taskcards and reports)")
print(f"- **Most active branch**: fix/env-gates-20260128-1615 ({max((b['unmerged'] for b in unmerged_branches), default=0)} unmerged commits)")
print(f"- **Current branch**: feat/golden-2pilots-20260201 (10 unmerged commits)")
print("- **Merge strategy needed**: Many TC branches appear to be sequential work that needs coordinated merging")
print("- **Risk of conflicts**: High - many branches touching similar areas (plans/, src/, tests/)")
print()

