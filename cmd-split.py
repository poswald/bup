#!/usr/bin/env python
import sys, time, re
import hashsplit, git, options
from helpers import *

optspec = """
bup split [-tcb] [-n name] [--bench] [filenames...]
--
r,remote=  remote repository path
b,blobs    output a series of blob ids
t,tree     output a tree id
c,commit   output a commit id
n,name=    name of backup set to update (if any)
v,verbose  increase log output (can be used more than once)
bench      print benchmark timings to stderr
"""
o = options.Options('bup split', optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

git.check_repo_or_die()
if not (opt.blobs or opt.tree or opt.commit or opt.name):
    log("bup split: use one or more of -b, -t, -c, -n\n")
    o.usage()

hashsplit.split_verbosely = opt.verbose
if opt.verbose >= 2:
    git.verbose = opt.verbose - 1
    opt.bench = 1

start_time = time.time()

def server_connect(remote):
    rs = remote.split(':', 1)
    if len(rs) == 1:
        p = subprocess.Popen(['bup', 'server', '-d', opt.remote],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    else:
        (host, dir) = rs
        p = subprocess.Popen(['ssh', host, '--', 'bup', 'server'],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        dir = re.sub(r'[\r\n]', ' ', dir)
        p.stdin.write('set-dir\n%s\n' % dir)
    return p

if opt.remote:
    p = server_connect(opt.remote)
    p.stdin.write('receive-objects\n')
    w = git.PackWriter_Remote(p.stdin)
else:
    w = git.PackWriter()
    
(shalist,tree) = hashsplit.split_to_tree(w, hashsplit.autofiles(extra))

if opt.verbose:
    log('\n')
if opt.blobs:
    for (mode,name,bin) in shalist:
        print bin.encode('hex')
if opt.tree:
    print tree.encode('hex')
if opt.commit or opt.name:
    msg = 'bup split\n\nGenerated by command:\n%r' % sys.argv
    ref = opt.name and ('refs/heads/%s' % opt.name) or None
    commit = w.new_commit(ref, tree, msg)
    if opt.commit:
        print commit.encode('hex')

if opt.remote:
    w.close()
    p.stdin.write('quit\n')
    p.wait()

secs = time.time() - start_time
size = hashsplit.total_split
if opt.bench:
    log('\nbup: %.2fkbytes in %.2f secs = %.2f kbytes/sec\n'
        % (size/1024., secs, size/1024./secs))
