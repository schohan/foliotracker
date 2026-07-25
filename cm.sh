#! /bin/bash


# Git add. commit. push. shortcut

echo "Adding files to git"
git add .

echo "Committing files to git"
if [ -n "$1" ]; then
    git commit -m "$1"
else
    git commit -m "updated"
fi

echo "Pushing files to git"
git push

echo "Done"