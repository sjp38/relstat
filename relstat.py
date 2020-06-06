#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys

def cmd_str_output(cmd):
    output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
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
            version_list = [major_version, minor_version]
            if len(minors) == 2:
                rc = int(minors[1], 10)
                version_list.append(rc)
            versions.append(version_list)
        except:
            continue
    return sorted(versions)

def version_name(v):
    if len(v) == 2:
        return 'v%d.%d' % (v[0], v[1])
    return 'v%d.%d-rc%d' % (v[0], v[1], v[2])

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
        versions = get_versions()[-20:]

    for idx, v in enumerate(versions):
        if idx == 0:
            continue
        from_ = version_name(versions[idx - 1])
        to = version_name(v)
        from_to = '%s..%s' % (from_, to)
        print(from_to)
        stat = gitcmd_str_output(['diff', '--shortstat', from_to])
        print(stat)

if __name__ == '__main__':
    main()
