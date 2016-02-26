#! /usr/bin/env python

import argparse
import time
import subprocess
import sys

from apiclient import sample_tools
from oauth2client import client
from subprocess import CalledProcessError

"""
A script to push releases to Google Play
See samples: https://github.com/googlesamples/android-play-publisher-api

Requires Google API python client
Insall with: pip install google-api-python-client
"""

PACKAGE = 'com.thebluealliance.androidclient'
CHANGELOG_PATH = 'android/src/prod/play/en-US/whatsnew'
INAPP_CHANGELOG = 'android/src/main/res/raw/changelog.txt'
APK_PATH_FORMAT = 'android/build/apk/tba-android-v{}-release.apk'
SHORTLOG_PATH = 'RELEASE_SHORTLOG'

parser = argparse.ArgumentParser(add_help=True)
parser.add_argument("tag", help="New version number (e.g. 3.1.4)")
parser.add_argument("--message", "-m", help="Tag message. Defaults to 'Version v<tag>'")
parser.add_argument("--skip-tag", action="store_true", default=False,
                    help="Do not make a new git tag. Instead, push existing release identified by <tag>")
parser.add_argument("--dirty-repo", action="store_true", default=False,
                    help="Allow untracked changes in the repo")
parser.add_argument("--skip-validate", action="store_true", default=False,
                    help="Do not build an install the prod apk to test on a real device")
parser.add_argument("--skip-gh", action="store_true", default=False,
                    help="Do not create a new release on GitHub")


def check_clean_repo():
    try:
        subprocess.check_output(["git", "diff-files", "--quiet", "--ignore-submodules"])
    except CalledProcessError:
        print "You have uncommitted changes in the repository. Commit them and try again"
        sys.exit(1)


def check_unittest():
    print "Running project unit tests..."
    time.sleep(2)
    try:
        subprocess.check_call(["./gradlew", "testProdReleaseUnitTest"])
        print "Unit tests passed!"
    except CalledProcessError:
        print "Unit tests failed. Fix them before releasing"
        sys.exit(1)


def update_whatsnew():
    print "Updating whatsnew file ({}). Limit 500 characters".format(CHANGELOG_PATH)
    time.sleep(2)
    base_tag = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"]).split()[0]
    commitlog = subprocess.check_output(["git", "shortlog", "{}..HEAD".format(base_tag), "--oneline", "--no-merges"])
    commitlog = '# '.join(('\n' + commitlog.lstrip()).splitlines(True))

    # Append commented commitlog to whatsnew file for ease of writing
    with open(CHANGELOG_PATH, "a") as whatsnew:
        whatsnew.write(commitlog)

    subprocess.call(["vim", CHANGELOG_PATH])

    # Remove "commented" commitlog lines
    subprocess.call(["sed", "-i", "/^#/d", CHANGELOG_PATH])

    # Check character count
    chars = subprocess.check_output(["wc", "-m", CHANGELOG_PATH])
    if int(chars.split()[0]) > 500:
        print "Changelog too long. Must be limited to 500 characters"
        sys.exit(1)

    # Copy to in-app changelog
    subprocess.call(["cp", CHANGELOG_PATH, INAPP_CHANGELOG])

    # Fix line breaks
    subprocess.call(["sed", "-i", 's/$/<br>/', INAPP_CHANGELOG])
    subprocess.call(["rm", "-f", "{}{}".format(INAPP_CHANGELOG, "bak")])


def commit_whatsnew():
    print "Committing new changelog"
    time.sleep(2)
    subprocess.call(["git", "add", INAPP_CHANGELOG, CHANGELOG_PATH])
    try:
        subprocess.check_output(["git", "commit", "-m", "Version {} Whatsnew".format(args.tag)])
    except CalledProcessError:
        print "Unable to commit new changelog"
        sys.exit(1)

    # Write shortlog to file
    base_tag = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"]).split()[0]
    shortlog = subprocess.check_output(["git", "shortlog", "{}..HEAD".format(base_tag), "--no-merges", "--oneline"])
    with open(SHORTLOG_PATH, "w") as logfile:
        logfile.write(shortlog)


def create_tag(args):
    # Add the git tag
    name = args.message if args.message else "Version {}".format(args.tag)
    print("Creating new git tag for release v{}: {}".format(args.tag, name))
    print("To skip creating a new tag, run with --skip_tag")
    time.sleep(2)
    subprocess.call(["git", "tag", "-a", "v{}".format(args.tag), "-m", name])


def validate_build():
    print "Installing build, ensure a device is plugged in with USB Debugging enabled"
    subprocess.call(["adb", "devices"])
    try:
        input("Press Enter to continue...")
    except SyntaxError:
        pass
    time.sleep(5)
    subprocess.check_call(["./gradlew", "installProdRelease"])
    subprocess.call(["adb", "shell", "am", "start", "-n", "com.thebluealliance.androidclient/com.thebluealliance.androidclient.activities.LaunchActivity"])
    try:
        input("Press Enter to continue the release, or ^C to quit")
    except SyntaxError:
        pass


def build_apk(args):
    # Check out repo at specified tag and build
    old_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip()
    print "Leaving {}, checking out tag v{}".format(old_branch, args.tag)
    time.sleep(2)
    subprocess.call(["git", "checkout", "v{}".format(args.tag)])
    print "Building and uploading the app..."
    time.sleep(2)
    subprocess.call(["./gradlew", "publishProdRelease"])
    print "Returning to {}".format(old_branch)
    subprocess.call(["git", "checkout", old_branch])


def push_repo():
    subprocess.call(["git", "push", "upstream"])
    subprocess.call(["git", "push", "--tags", "upstream"])


def create_release(args):
    apk_path = APK_PATH_FORMAT.format(args.tag)
    title = "Version {}".format(args.tag)
    tag = "v{}".format(args.tag)
    subprocess.call(["scripts/github_release.sh", tag, title, CHANGELOG_PATH, SHORTLOG_PATH, apk_path])

if __name__ == "__main__":
    args = parser.parse_args()
    if not args.dirty_repo:
        check_clean_repo()
    check_unittest()
    if not args.skip_tag:
        update_whatsnew()
        commit_whatsnew()
        create_tag(args)
    if not args.skip_validate:
        validate_build()
    build_apk(args)
    push_repo()
    create_release(args)
