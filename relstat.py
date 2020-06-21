#!/usr/bin/env python3

import argparse
import datetime
import os
import subprocess
import sys

class VersionStat:
    version = None
    prev_version = None
    files_to_stat = None
    changed_files = None
    deletions = None
    insertions = None
    diff = None

    def __init__(self, version, prev_version, files_to_stat):
        self.version = version
        self.prev_version = prev_version
        self.files_to_stat = files_to_stat

        self.set_stat()

    def set_stat(self):
        commit_range = '%s..%s' % (self.prev_version, self.version)
        stat_options = ['diff', '--shortstat', commit_range]
        if self.files_to_stat:
            stat_options += ['--'] + self.files_to_stat
        stat = gitcmd_str_output(stat_options)

        # e.g., '127 files changed, 7926 insertions(+), 3954 deletions(-)'
        stat_field = stat.split()
        if len(stat_field) >= 3 and stat_field[1] == 'files':
            self.changed_files = int(stat_field[0])
            stat_field = stat_field[3:]
        else:
            self.changed_files = 0
        if len(stat_field) >= 2 and stat_field[1].startswith('insertions(+)'):
            self.insertions = int(stat_field[0])
            stat_field = stat_field[2:]
        else:
            self.insertions = 0
        if len(stat_field) == 2 and stat_field[1].startswith('deletions(-)'):
            self.deletions = int(stat_field[0])
        else:
            self.deletions = 0
        self.diff = self.insertions + self.deletions

    def pr_stat(self, dateonly):
        commit_date = version_commit_date(self.version)
        if dateonly:
            version = commit_date.date()
        else:
            version = '%s(%s)' % (self.version, commit_date.date())

        print('%22s %10s %10s %10s %10s'
                % (version, self.changed_files, self.deletions,
                    self.insertions, self.diff))

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

def order_str(order):
    last_digit = order % 10
    if last_digit == 1:
        return '%sst' % order
    if last_digit == 2:
        return '%snd' % order
    if last_digit == 3:
        return '%srd' % order
    return '%sth' % order

def pr_report(stat, stats):
    nr_versions = len(stats)
    print('# Among the %d releases, %s has' % (nr_versions, stat.version))

    order = sorted(stats, key=lambda x: x.changed_files).index(stat) + 1
    print('#    %s smallest file changes' % order_str(order))
    order = sorted(stats, key=lambda x: x.insertions).index(stat) + 1
    print('#    %s smallest insertions' % order_str(order))
    order = sorted(stats, key=lambda x: x.deletions).index(stat) + 1
    print('#    %s smallest deletions' % order_str(order))
    order = sorted(stats, key=lambda x: x.diff).index(stat) + 1
    print('#    %s smallest diffs' % order_str(order))

def set_argparser(parser):
    parser.add_argument('--gitdir', metavar='<dir>', default='./.git',
            help='git directory of the project')
    parser.add_argument('--versions', metavar='<version>', nargs='+',
            help='versions to make stat')
    parser.add_argument('--versions_file', metavar='<file>',
            help='file containing the versions to make stat')
    parser.add_argument('--base_versions', metavar='<version>', nargs='+',
            help='versions to use as baseline of the releases')
    parser.add_argument('--base_versions_file', metavar='<file>',
            help='file containing the versions to use as the baselines')
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
    parser.add_argument('--sortby',
            choices=['files', 'deletions', 'insertions', 'diff'],
            help='sort stat with the given key')

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

    base_versions = args.base_versions
    if not base_versions and args.base_versions_file:
        if not os.path.exists(args.base_versions_file):
            print('Wrong base versions file \'%s\'' % args.base_versions_file)
            exit(1)
        with open(args.base_versions_file, 'r') as f:
            base_versions = [x.strip() for x in f.read().split('\n')]

    if not base_versions:
        base_versions = [versions[0]] + versions[:-1]
    if len(base_versions) != len(versions):
        print('len(base_versions) != len(versions)')
        exit(1)

    files_to_stat = args.files_to_stat

    report_for = args.report_for

    stats_map = {}

    print('%22s %10s %10s %10s %10s' %
            ('version', 'files', 'deletions', 'insertions', 'diff'))
    for idx, v in enumerate(versions):
        if base_versions[idx] == v:
            continue

        try:
            extra_version = v.split('-')[1]
            if args.extra_version and extra_version != args.extra_version:
                continue
        except:
            if args.extra_version:
                continue

        if not args.report_for:
            report_for = v

        stat = VersionStat(v, base_versions[idx], files_to_stat)
        if not args.sortby:
            stat.pr_stat(args.dateonly)
        stats_map[v] = stat

    stats = list(stats_map.values())

    if args.sortby:
        if args.sortby == 'changed_files':
            stats = sorted(stats, key=lambda x: x.changed_files)
        elif args.sortby == 'insertions':
            stats = sorted(stats, key=lambda x: x.insertions)
        elif args.sortby == 'deletions':
            stats = sorted(stats, key=lambda x: x.deletions)
        elif args.sortby == 'diff':
            stats = sorted(stats, key=lambda x: x.diff)
        for s in stats:
            s.pr_stat(args.dateonly)

    nr_stats = len(stats)
    print('%22s %10.0f %10.0f %10.0f %10.0f' %
            ('# avg', sum(s.changed_files for s in stats) / nr_stats,
                sum(s.deletions for s in stats) / nr_stats,
                sum(s.insertions for s in stats) / nr_stats,
                sum(s.diff for s in stats) / nr_stats))
    print('%22s %10.0f %10.0f %10.0f %10.0f' %
            ('# min', min(s.changed_files for s in stats),
                min(s.deletions for s in stats),
                min(s.insertions for s in stats),
                min(s.diff for s in stats)))
    print('%22s %10.0f %10.0f %10.0f %10.0f' %
            ('# max', max(s.changed_files for s in stats),
                max(s.deletions for s in stats),
                max(s.insertions for s in stats),
                max(s.diff for s in stats)))
    print('%22s %10.0f %10.0f %10.0f %10.0f' %
            ('# total', sum(s.changed_files for s in stats),
                sum(s.deletions for s in stats),
                sum(s.insertions for s in stats),
                sum(s.diff for s in stats)))

    if report_for in stats_map:
        pr_report(stats_map[report_for], stats)

if __name__ == '__main__':
    main()
