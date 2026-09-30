#!/usr/bin/env perl
# Flatten an HTML draft to the prose a reader actually sees, for the writing
# gate to scan.
#
# The gate reports line numbers, and a report whose numbers do not match the
# file on disk is worse than no report. So this does not convert to Markdown,
# which would renumber everything. It emits one line per source line, and puts
# each block of prose on the line where that block STARTS. Everything else is
# blank. Line numbers survive, and a sentence that the source wrapped over four
# lines arrives as one line the gate can measure.
#
# What it drops, because none of it is prose the reader sees:
#   - <style> and <script> contents, so CSS declarations stop tripping the
#     semicolon rule
#   - HTML comments, which on a client-facing page are notes to ourselves
#   - the tags themselves
#
# What it decodes: character entities. Without this the em dash rule counts
# `&mdash;` as nothing, and scored 1 against a true 34 on a real draft.
#
# Why perl, when the house rule is a uv script with inline PEP 723 deps:
# `uv` is mise-managed and is not on the base PATH. Under a non-login shell a
# uv-shebang script fails with "env: uv: No such file or directory", and a hook
# is not guaranteed a login shell. /usr/bin/perl is always there, and
# writing-gate.sh is already bash wrapping an inline perl scanner, so this adds
# no dependency the gate did not already have. A uv version was written and
# benchmarked on 2026-08-27: byte-identical output, 37ms against 16ms per run.
# The speed was never the point; the PATH was.
#
# Usage: html-prose.pl FILE   (writes to stdout)

use strict;
use warnings;
use HTML::Parser ();
use HTML::Entities ();

binmode STDOUT, ':encoding(UTF-8)';

my ($path) = @ARGV;
die "usage: html-prose.pl FILE\n" unless defined $path;
open my $fh, '<:encoding(UTF-8)', $path or die "cannot read $path: $!\n";
my $html = do { local $/; <$fh> };
close $fh;

my $total_lines = ($html =~ tr/\n//);
# A file that does not end in a newline still has a last line.
$total_lines++ if length $html and $html !~ /\n\z/;

# Tags that end a block of prose. An inline tag such as <strong> or <span> must
# not, or every emphasised phrase would become its own sentence.
my %BLOCK = map { $_ => 1 } qw(
    p h1 h2 h3 h4 h5 h6 li td th tr blockquote cite caption
    div section article header footer aside main figcaption
    dt dd pre ul ol dl table thead tbody form
);

# Contents are markup or styling, never prose.
my %OPAQUE = map { $_ => 1 } qw(style script noscript template svg);

my @out = ('') x $total_lines;
my $buf   = '';
my $start = undef;
my $depth = 0;    # inside how many opaque elements

sub flush {
    return unless defined $start;
    my $text = $buf;
    $text =~ s/\s+/ /g;
    $text =~ s/^ | $//g;
    if (length $text) {
        # Two blocks can start on one source line, e.g. <td>a</td><td>b</td>.
        # Join rather than overwrite, so nothing is silently lost.
        $out[$start] = length $out[$start] ? "$out[$start] $text" : $text;
    }
    $buf   = '';
    $start = undef;
}

my $p = HTML::Parser->new(api_version => 3);

$p->handler(
    start => sub {
        my ($tag, $line) = @_;
        if ($OPAQUE{$tag}) { flush(); $depth++; return }
        return if $depth;
        flush() if $BLOCK{$tag};
        flush() if $tag eq 'br';
    },
    'tagname, line'
);

$p->handler(
    end => sub {
        my ($tag) = @_;
        if ($OPAQUE{$tag}) { $depth-- if $depth; return }
        return if $depth;
        flush() if $BLOCK{$tag};
    },
    'tagname'
);

$p->handler(
    text => sub {
        my ($text, $line) = @_;
        return if $depth;
        # Whitespace between two inline tags is a word gap. Dropping it welds
        # `<span>a</span> <span>b</span>` into "ab".
        if ($text !~ /\S/) { $buf .= ' ' if length $buf; return }
        $start = $line - 1 unless defined $start;
        $buf .= $text;
    },
    'dtext, line'
);

# Comments and declarations have no handler, so they never reach the output.

$p->parse($html);
$p->eof;
flush();

# Guard against a block whose start line ran past the file, which malformed
# markup can produce.
print "$_\n" for map { defined $_ ? $_ : '' } @out[ 0 .. $total_lines - 1 ];
