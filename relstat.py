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

def get_versions(since, before):
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
            cdate = version_commit_date(version)
            if cdate > since and cdate < before:
                versions.append(version)
        except:
            continue
    return versions

def main():
    global git_cmd

    parser = argparse.ArgumentParser()
    parser.add_argument('--gitdir', metavar='<dir>', default='./.git',
            help='git directory of the project')
    parser.add_argument('--versions', metavar='<version>', nargs='+',
            help='versions to make stat')
    parser.add_argument('--nr_releases', metavar='<number>', type=int,
            help='number of latest releases to make statistics')
    parser.add_argument('--since', metavar='<date (YYYY-MM-DD)>',
            help='show stat of releases since this date')
    parser.add_argument('--before', metavar='<date (YYYY-MM-DD)>',
            help='show stat of releases before this date')
    parser.add_argument('--extra_version', metavar='<extra version name>',
            help='show stat for specific extra versions only')
    args = parser.parse_args()

    if not os.path.isdir(args.gitdir) or not os.path.exists(args.gitdir):
        print('Wrong git directory \'%s\'' % args.gitdir)
    git_cmd = ['git', '--git-dir=%s' % args.gitdir]

    versions = args.versions
    if not versions:
        if args.since:
            since = datetime.datetime.strptime(args.since, '%Y-%m-%d')
        else:
            since = datetime.datetime.now() - datetime.timedelta(days=2 * 365)
        if args.before:
            before = datetime.datetime.strptime(args.before, '%Y-%m-%d')
        else:
            before = datetime.datetime.now()
        versions = get_versions(since, before)
    versions = sorted(versions, key=lambda x: version_commit_date(x))

    nr_releases = 20
    if args.nr_releases:
        nr_releases = args.nr_releases

    changed_files = []
    insertions = []
    deletions = []

    print('%22s %10s %10s %10s %10s' %
            ('version', 'files', 'inserts', 'deletes' ,'diff'))
    for idx, v in enumerate(versions):
        if idx == 0:
            from_ = v
        else:
            from_ = versions[idx - 1]
        to = v
        from_to = '%s..%s' % (from_, to)

        try:
            extra_version = v.split('-')[1]
            if args.extra_version and extra_version != args.extra_version:
                continue
        except:
            if args.extra_version:
                continue

        if nr_releases == 0:
            break
        nr_releases -= 1

        stat = gitcmd_str_output(['diff', '--shortstat', from_to])
        # e.g., '127 files changed, 7926 insertions(+), 3954 deletions(-)'
        stat_field = stat.split()
        if len(stat_field) >= 3 and stat_field[1] == 'files':
            changed_files.append(int(stat_field[0]))
            stat_field = stat_field[3:]
        else:
            changed_files.append(0)
        if len(stat_field) >= 2 and stat_field[1].startswith('insertions(+)'):
            insertions.append(int(stat_field[0]))
            stat_field = stat_field[2:]
        else:
            insertions.append(0)
        if len(stat_field) == 2 and stat_field[1].startswith('deletions(-)'):
            deletions.append(int(stat_field[0]))
        else:
            deletions.append(0)

        print('%10s(%s) %10s %10s %10s %10s'
                % ( v, version_commit_date(v).date(),
                    changed_files[-1], insertions[-1], deletions[-1],
                    insertions[-1] + deletions[-1]))

    # Remove first stats, as it is all zero
    changed_files = changed_files[1:]
    insertions = insertions[1:]
    deletions = deletions[1:]
    diffs = [x + y for x,y in zip(insertions, deletions)]

    print('%22s %10.0f %10.0f %10.0f %10.0f' %
            ('# avg', sum(changed_files) / len(changed_files),
                sum(insertions) / len(insertions),
                sum(deletions) / len(deletions),
                sum(diffs) / len(diffs)))
    print('%22s %10s %10s %10s %10s' %
            ('# min', min(changed_files), min(insertions), min(deletions),
                min(diffs)))
    print('%22s %10s %10s %10s %10s' %
            ('# max', max(changed_files), max(insertions), max(deletions),
                max(diffs)))
    print('%22s %10s %10s %10s %10s' %
            ('# total', sum(changed_files), sum(insertions), sum(deletions),
                sum(diffs)))

if __name__ == '__main__':
    main()
