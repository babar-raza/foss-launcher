#!/bin/bash
MAIN="main"

# Read branches from activity table (skip header) and process
tail -n +2 branches_activity.tsv | while IFS=$'\t' read -r branch last_date commits_8d ahead behind unmerged; do
  # Skip if no unmerged commits
  if [ "$unmerged" -eq 0 ]; then
    continue
  fi
  
  # Sanitize branch name for filename
  safe_name=$(echo "$branch" | sed 's|/|_|g' | sed 's|origin_||')
  
  # Save commit list for last 8 days
  git log --oneline --decorate --since="8 days ago" "$branch" > "branch_${safe_name}_commits_8d.txt" 2>/dev/null
  
  # Save unmerged commit list
  git log --oneline --decorate --since="8 days ago" $MAIN.."$branch" > "branch_${safe_name}_UNMERGED_8d.txt" 2>/dev/null
  
  # Save diff summary vs MAIN (merge-base aware)
  git diff --name-status $MAIN..."$branch" > "branch_${safe_name}_name_status.txt" 2>/dev/null
  
  # Save diff stat
  git diff --stat $MAIN..."$branch" > "branch_${safe_name}_diffstat.txt" 2>/dev/null
done

echo "Branch details captured"
