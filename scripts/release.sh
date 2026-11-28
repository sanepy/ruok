#!/usr/bin/env bash
# Bump version tag and push
set -euo pipefail

current_branch=$(git rev-parse --abbrev-ref HEAD)

if [ "$current_branch" != "master" ]; then
  echo "Error: not on master. Current branch is $current_branch."
  exit 1
fi

echo "Fetching origin..."
git fetch origin
behind=$(git rev-list --count HEAD..origin/master)

if [ "$behind" -gt 0 ]; then
  echo "Error: master is $behind commit(s) behind origin/master. Run 'git pull' first."
  exit 1
fi

latest_tag=$(git describe --tags --abbrev=0 --match "v*" 2>/dev/null || echo "")
highest_tag=$(git tag --list "v*" | sort -V | tail -n 1)

if [ -n "$highest_tag" ] && [ -z "$latest_tag" ]; then
  echo "Error: tags exist but none is reachable from HEAD. Newest tag is $highest_tag."
  exit 1
fi

if [ -n "$highest_tag" ] && [ "$highest_tag" != "$latest_tag" ]; then
  echo "Warning: highest tag is $highest_tag, but the last tag reachable"
  echo "from HEAD is $latest_tag. Bumping from $latest_tag."
fi

if [ -z "$latest_tag" ]; then
  echo "No existing v* tags found. This will be the first release."
  current="v0.0.0"
else
  current="$latest_tag"
  echo "Current tag: $current"
  echo ""
  echo "Commits since $current:"
  git --no-pager log "$current..HEAD" --oneline 2>/dev/null || echo "  (no new commits)"
fi

raw_version="${current#v}"
IFS='.' read -r major minor patch <<< "$raw_version"

patch_bump="v${major}.${minor}.$((patch + 1))"
minor_bump="v${major}.$((minor + 1)).0"
major_bump="v$((major + 1)).0.0"

echo ""
echo "What kind of bump?"
echo "  1) patch  ($current → $patch_bump)"
echo "  2) minor  ($current → $minor_bump)"
echo "  3) major  ($current → $major_bump)"
echo ""
read -rp "Choice [1/2/3]: " choice

case "$choice" in
  1) new_tag="$patch_bump" ;;
  2) new_tag="$minor_bump" ;;
  3) new_tag="$major_bump" ;;
  *) echo "Invalid choice"; exit 1 ;;
esac

echo ""
echo "New tag: $new_tag"
read -rp "Confirm and push? [y/N]: " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
  echo "Aborted."
  exit 0
fi

git tag -a "$new_tag" -m "Release $new_tag"
git push --atomic origin "$current_branch" "$new_tag"
echo "Pushed $new_tag and $current_branch. Check https://github.com/sanepy/ruok/actions"
echo "To override the auto release notes once CI has created the release:"
echo "  gh release edit $new_tag --notes '...'   # or --notes-file notes.md"
