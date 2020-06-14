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
        '--date=unix']).split('\n')[0]
    return datetime.datetime.utcfromtimestamp(int(date))

def is_valid_version(v):
    try:
        date = gitcmd_str_output(['log', '%s^..%s' % (v, v), '--pretty=%cd',
            '--date=unix']).split('\n')[0]
    except subprocess.CalledProcessError:
        return False
    return True

def get_stable_versions(major_version, since, before):
    versions_all = gitcmd_str_output(['tag']).split('\n')

    versions = []
    for version in versions_all:
        # '<major_version>.[0-9]+' are stable release
        if not version.startswith(major_version + '.'):
            continue
        try:
            stable_version_number = int(version[len(major_version) + 1:])
        except:
            continue
        cdate = version_commit_date(version)
        if cdate > since and cdate < before:
            versions.append(version)
    return versions

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

def pr_report(version, changed_files, insertions, deletions, diffs):
    nr_versions = len(changed_files)
    print('# Among the %d releases, %s has' % (nr_versions, version))
    order = sorted(list(changed_files.values())).index(changed_files[version])
    print('#    %dth smallest file changes' % order)
    order = sorted(list(insertions.values())).index(insertions[version])
    print('#    %dth smallest insertions' % order)
    order = sorted(list(deletions.values())).index(deletions[version])
    print('#    %dth smallest deletions' % order)
    order = sorted(list(diffs.values())).index(diffs[version])
    print('#    %dth smallest diffs' % order)

def set_argparser(parser):
    parser.add_argument('--gitdir', metavar='<dir>', default='./.git',
            help='git directory of the project')
    parser.add_argument('--versions', metavar='<version>', nargs='+',
            help='versions to make stat')
    parser.add_argument('--versions_file', metavar='<file>',
            help='file containing the versions to make stat')
    parser.add_argument('--since', metavar='<date (YYYY-MM-DD)>',
            help='show stat of releases since this date')
    parser.add_argument('--before', metavar='<date (YYYY-MM-DD)>',
            help='show stat of releases before this date')
    parser.add_argument('--extra_version', metavar='<extra version name>',
            help='show stat for specific extra versions only')
    parser.add_argument('--stables', metavar='<major version name>',
            help='show stat for stable releases of specific major version')
    parser.add_argument('--files_to_stat', metavar='<file>', nargs='+',
            help='files and/or directories to make stat for')

    parser.add_argument('--dateonly', action='store_true',
            help='show release date only')
    parser.add_argument('--report_for', metavar='<version>',
            help='print brief report for the version')

def main():
    global git_cmd

    parser = argparse.ArgumentParser()
    set_argparser(parser)
    args = parser.parse_args()

    if not os.path.isdir(args.gitdir) or not os.path.exists(args.gitdir):
        print('Wrong git directory \'%s\'' % args.gitdir)
    git_cmd = ['git', '--git-dir=%s' % args.gitdir]

    versions = args.versions

    if not versions and args.versions_file:
        if not os.path.exists(args.versions_file):
            print('Wrong versions file \'%s\'' % args.versions_file)
            exit(1)
        with open(args.versions_file, 'r') as f:
            versions = [x.strip() for x in f.read().split('\n')]

    if not versions:
        if args.since:
            since = datetime.datetime.strptime(args.since, '%Y-%m-%d')
        else:
            since = datetime.datetime.now() - datetime.timedelta(days=30 * 6)
        if args.before:
            before = datetime.datetime.strptime(args.before, '%Y-%m-%d')
        else:
            before = datetime.datetime.now()

        if args.stables:
            versions = get_stable_versions(args.stables, since, before)
        else:
            versions = get_versions(since, before)
            master_date = version_commit_date('master')
            if master_date > since and master_date < before:
                versions.append('master')
    versions = [v for v in versions if is_valid_version(v)]
    versions = sorted(versions, key=lambda x: version_commit_date(x))
    if not versions:
        exit()

    files_to_stat = args.files_to_stat

    changed_files = {}
    insertions = {}
    deletions = {}
    diffs = {}

    print('%22s %10s %10s %10s %10s' %
            ('version', 'files', 'deletions', 'insertions', 'diff'))
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

        stat_options = ['diff', '--shortstat', from_to]
        if files_to_stat:
            stat_options += ['--'] + files_to_stat
        stat = gitcmd_str_output(stat_options)
        # e.g., '127 files changed, 7926 insertions(+), 3954 deletions(-)'
        stat_field = stat.split()
        if len(stat_field) >= 3 and stat_field[1] == 'files':
            changed_files[v] = int(stat_field[0])
            stat_field = stat_field[3:]
        else:
            changed_files[v] = 0
        if len(stat_field) >= 2 and stat_field[1].startswith('insertions(+)'):
            insertions[v] = int(stat_field[0])
            stat_field = stat_field[2:]
        else:
            insertions[v] = 0
        if len(stat_field) == 2 and stat_field[1].startswith('deletions(-)'):
            deletions[v] = int(stat_field[0])
        else:
            deletions[v] = 0
        diffs[v] = insertions[v] + deletions[v]

        if args.dateonly:
            version = '%22s' % version_commit_date(v).date()
        else:
            version = '%10s(%s)' % (v, version_commit_date(v).date())

        print('%22s %10s %10s %10s %10s'
                % (version, changed_files[v], deletions[v], insertions[v],
                    insertions[v] + deletions[v]))

    # Remove first stats, as it is all zero
    if versions[0] in changed_files:
        del changed_files[versions[0]]
        del insertions[versions[0]]
        del deletions[versions[0]]
        del diffs[versions[0]]

    print('%22s %10.0f %10.0f %10.0f %10.0f' %
            ('# avg', sum(changed_files.values()) / len(changed_files),
                sum(deletions.values()) / len(deletions),
                sum(insertions.values()) / len(insertions),
                sum(diffs.values()) / len(diffs)))
    print('%22s %10s %10s %10s %10s' %
            ('# min', min(changed_files.values()), min(deletions.values()),
                min(insertions.values()), min(diffs.values())))
    print('%22s %10s %10s %10s %10s' %
            ('# max', max(changed_files.values()), max(deletions.values()),
                max(insertions.values()), max(diffs.values())))
    print('%22s %10s %10s %10s %10s' %
            ('# total', sum(changed_files.values()), sum(deletions.values()),
                sum(insertions.values()), sum(diffs.values())))

    report_for = args.report_for
    if report_for and report_for in changed_files:
        pr_report(report_for, changed_files, insertions, deletions, diffs)

if __name__ == '__main__':
    main()
