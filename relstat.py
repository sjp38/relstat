#!/usr/bin/env python3

import argparse
import datetime
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

def version_commit_date(v):
    date = gitcmd_str_output(['log', '%s^..%s' % (v, v), '--pretty=%cd',
        '--date=unix'])
    return datetime.datetime.utcfromtimestamp(int(date))

def version_name(v):
    if v[2] == 999:
        return 'v%d.%d' % (v[0], v[1])
    return 'v%d.%d-rc%d' % (v[0], v[1], v[2])

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
                if rc >= 999:
                    print('rc version (%d) >=999' % rc)
                    exit(-1)
            else:
                rc = 999
            version_list.append(rc)
            versions.append(version_list)
        except:
            continue
    return [version_name(v) for v in sorted(versions)]

def main():
    global git_cmd

    parser = argparse.ArgumentParser()
    parser.add_argument('--gitdir', metavar='<dir>', default='./.git',
            help='git directory of the project')
    parser.add_argument('--versions', metavar='<version>', nargs='+',
            help='versions to make stat')
    parser.add_argument('--nr_releases', metavar='<number>', type=int,
            help='number of latest releases to make statistics')
    args = parser.parse_args()

    if not os.path.isdir(args.gitdir) or not os.path.exists(args.gitdir):
        print('Wrong git directory \'%s\'' % args.gitdir)
    git_cmd = ['git', '--git-dir=%s' % args.gitdir]

    versions = args.versions
    if not versions:
        nr_releases = 20
        if args.nr_releases:
            nr_releases = args.nr_releases
        versions = get_versions()[-1 * nr_releases:]

    changed_files = []
    insertions = []
    deletions = []
    for idx, v in enumerate(versions):
        if idx == 0:
            continue
        from_ = versions[idx - 1]
        to = v
        from_to = '%s..%s' % (from_, to)
        stat = gitcmd_str_output(['diff', '--shortstat', from_to])
        # e.g., '127 files changed, 7926 insertions(+), 3954 deletions(-)'
        stat_field = stat.split()
        changed_files.append(int(stat_field[0]))
        insertions.append(int(stat_field[3]))
        deletions.append(int(stat_field[5]))

        print('%20s (%s): %10s files, %10s insertions, %10s deletions' % (
            from_to, version_commit_date(v).date(),
            stat_field[0], stat_field[3], stat_field[5]))

    print()
    print('changed files (min, max, avg): %d, %d, %d' %
            (min(changed_files), max(changed_files),
                sum(changed_files) / len(changed_files)))

    print('insertions (min, max, avg): %d, %d, %d' %
            (min(insertions), max(insertions),
                sum(insertions) / len(insertions)))

    print('deletions (min, max, avg): %d, %d, %d' %
            (min(deletions), max(deletions),
                sum(deletions) / len(deletions)))

if __name__ == '__main__':
    main()
