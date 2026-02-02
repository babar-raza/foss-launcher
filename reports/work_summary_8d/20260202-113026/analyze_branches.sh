#!/bin/bash
MAIN="main"
echo -e "branch\tlast_commit_date\tcommits_in_8d\tahead_of_main\tbehind_main\tunmerged_in_8d"

# Analyze all local branches
while IFS= read -r branch; do
  # Get last commit date
  last_date=$(git log -1 --format="%ai" "$branch" 2>/dev/null || echo "N/A")
  
  # Count commits in last 8 days on this branch
  commits_8d=$(git log --oneline --since="8 days ago" "$branch" 2>/dev/null | wc -l)
  
  # Skip if no activity in last 8 days
  if [ "$commits_8d" -eq 0 ]; then
    continue
  fi
  
  # Count ahead/behind
  ahead=$(git rev-list --count $MAIN..$branch 2>/dev/null || echo "0")
  behind=$(git rev-list --count $branch..$MAIN 2>/dev/null || echo "0")
  
  # Count unmerged commits in last 8 days
  unmerged_8d=$(git log --oneline --since="8 days ago" $MAIN..$branch 2>/dev/null | wc -l)
  
  echo -e "$branch\t$last_date\t$commits_8d\t$ahead\t$behind\t$unmerged_8d"
done < branches_local.txt

# Also check remote branches
while IFS= read -r branch; do
  # Get last commit date
  last_date=$(git log -1 --format="%ai" "$branch" 2>/dev/null || echo "N/A")
  
  # Count commits in last 8 days on this branch
  commits_8d=$(git log --oneline --since="8 days ago" "$branch" 2>/dev/null | wc -l)
  
  # Skip if no activity in last 8 days or if it's main
  if [ "$commits_8d" -eq 0 ] || [ "$branch" = "origin/main" ]; then
    continue
  fi
  
  # Count ahead/behind
  ahead=$(git rev-list --count $MAIN..$branch 2>/dev/null || echo "0")
  behind=$(git rev-list --count $branch..$MAIN 2>/dev/null || echo "0")
  
  # Count unmerged commits in last 8 days
  unmerged_8d=$(git log --oneline --since="8 days ago" $MAIN..$branch 2>/dev/null | wc -l)
  
  echo -e "$branch\t$last_date\t$commits_8d\t$ahead\t$behind\t$unmerged_8d"
done < branches_remote.txt
