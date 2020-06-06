#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys

def cmd_str_output(cmd):
    output = subprocess.check_output(cmd)
    try:
        return output.decode('utf-8').strip()
    except UnicodeDecodeError as e:
        print('could not decode cmd (%s) output: %s' % (cmd, e))
        return output.decode('cp437').strip()

def gitcmd_str_output(cmd):
    return cmd_str_output(git_cmd + cmd)

def get_versions():
    versions_all = gitcmd_str_output(['tag']).split('\n')

    versions = []
    for version in versions_all:
        # Only 'v[0-9]+.[0-9]+[-rc[0-9]+]' are valid by default
        if not version.startswith('v'):
            continue
        version_numbers = version[1:].split('.')
        if len(version_numbers) != 2:
            continue
        try:
            major_version = int(version_numbers[0], 10)
        except:
            continue
        minors = version_numbers[1].split('-rc')
        if len(minors) > 2:
            continue
        try:
            minor_version = int(minors[0], 10)
            if len(minors) == 2:
                rc = int(minors[1], 10)
                if rc >= 999:
                    print('rc >= 999 makes no sense')
                    exit(1)
            else:
                rc = 999
        except:
            continue
        versions.append([major_version, minor_version, rc])
    return sorted(versions)

def main():
    global git_cmd

    parser = argparse.ArgumentParser()
    parser.add_argument('--gitdir', metavar='<dir>', default='./.git',
            help='git directory of the project')
    parser.add_argument('--versions', metavar='<version>', nargs='+',
            help='versions to make stat')
    args = parser.parse_args()

    if not os.path.isdir(args.gitdir) or not os.path.exists(args.gitdir):
        print('Wrong git directory \'%s\'' % args.gitdir)
    git_cmd = ['git', '--git-dir=%s' % args.gitdir]

    if not args.versions:
        versions = get_versions()

    for v in versions:
        print(v)

if __name__ == '__main__':
    main()
