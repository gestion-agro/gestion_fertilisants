#!/bin/bash

set -e

VERSION=$(git describe --tags --abbrev=0)

if [ -z "$VERSION" ]; then
    echo "Usage: ./make_release.sh 1.0.0"
    exit 1
fi

APP_NAME="Gestion_Fertilisant"
MAIN_FILE="app.py"

BUILD_DIR="build"
DIST_DIR="dist"
RELEASE_ROOT="releases"
RELEASE_DIR="releases/$VERSION"

echo "=============================="
echo "Build version $VERSION"
echo "=============================="

# nettoyer build précédent
rm -rf "$BUILD_DIR" "$DIST_DIR"

# build pyinstaller
pyinstaller --onefile "$MAIN_FILE" --name $APP_NAME

# créer dossier release
mkdir -p "$RELEASE_DIR"

# copier executable
cp "$DIST_DIR/$APP_NAME" "$RELEASE_DIR/"

# fichier version
echo "$VERSION" > "$RELEASE_DIR/version.txt"

# archive tar.gz (important pour futur updater)
cd "$RELEASE_DIR"
tar -czf "$APP_NAME-linux-$VERSION.tar.gz" "$APP_NAME" version.txt
cd ../../

echo ""
echo "Release créée : $RELEASE_DIR"
echo ""