#!/usr/bin/perl
use strict;
use warnings;

# Both the rules and the draft hold multi-byte characters. Read as bytes, a
# character class like [-—] matches one byte of the em dash, and the rule
# silently never fires.
binmode STDOUT, ':encoding(UTF-8)';

# --- rules -------------------------------------------------------------
# Only the fenced ```rules block counts. Every other line in the file is prose
# for a human, or a judgment rule the gate cannot check.
# Every argument but the last is a rule file. They are parsed in order, so a
# later file wins on maxwords: common.md comes first, the profile second.
my $draft_path = pop @ARGV;
my @rule_paths = @ARGV;

my (@res, @densities, $maxwords, $maxwords_msg, @malformed);
for my $rules_path (@rule_paths) {
    open my $rf, '<:encoding(UTF-8)', $rules_path or next;
    # A malformed line has to name its file now that there is more than one.
    my $name = $rules_path;
    $name =~ s{.*/}{};
    my $in_block = 0;
    while (my $line = <$rf>) {
        chomp $line;
        if (!$in_block) { $in_block = 1 if $line =~ /^```rules\s*$/; next }
        last if $line =~ /^```/;
        next if $line =~ /^\s*$/ or $line =~ /^#/;
        # Fields are tab separated. The kind comes first and the message last.
        # What sits between them depends on the kind.
        my ($kind, @rest) = split /\t/, $line;
        my $msg = @rest ? pop @rest : undef;
        my $ok  = 0;
        if (defined $msg and $kind eq 're' and @rest == 1) {
            # A rule file is hand-edited. One bad regex must not silence the gate.
            my $re = eval { qr/$rest[0]/ };
            if (defined $re) { push @res, [ $re, $msg ]; $ok = 1 }
        }
        elsif (defined $msg and $kind eq 'maxwords' and @rest == 1) {
            $maxwords     = $rest[0] + 0;
            $maxwords_msg = $msg;
            $ok           = 1;
        }
        elsif (defined $msg and $kind eq 'density' and @rest == 3) {
            # Two numbers: a floor count, then a rate per thousand words. One
            # number cannot serve as both, and overloading it exempts long drafts.
            my $re = eval { qr/$rest[0]/ };
            if (defined $re) { push @densities, [ $re, $rest[1] + 0, $rest[2] + 0, $msg ]; $ok = 1 }
        }
        # The promotion hook appends rules to these files. A rule written with
        # spaces instead of tabs looks present and never fires, so say so.
        push @malformed, "$name line $." unless $ok;
    }
    close $rf;
}

# --- draft -------------------------------------------------------------
open my $df, '<:encoding(UTF-8)', $draft_path or exit 0;
my @lines = <$df>;
close $df;
chomp @lines;

# Front matter and code samples are not prose. Blank them rather than drop
# them, so the line numbers reported still match the file on disk.
my $i = 0;
if (@lines and $lines[0] =~ /^---\s*$/) {
    my $close;
    for my $j (1 .. $#lines) {
        if ($lines[$j] =~ /^(?:---|\.\.\.)\s*$/) { $close = $j; last }
    }
    if (defined $close) {
        $lines[$_] = '' for 0 .. $close;
        $i = $close + 1;
    }
}
my $fenced = 0;
for (; $i <= $#lines; $i++) {
    if ($lines[$i] =~ /^\s*(?:```|~~~)/) { $fenced = !$fenced; $lines[$i] = ''; next }
    $lines[$i] = '' if $fenced;
    # A thematic break is punctuation, not a sentence.
    $lines[$i] = '' if !$fenced and $lines[$i] =~ /^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/;
    # So is a table's separator row, such as | --- | :-: |.
    $lines[$i] = '' if !$fenced and $lines[$i] =~ /^\s*\|?(?:\s*:?-+:?\s*\|)+(?:\s*:?-+:?\s*)?$/;
}

# --- scan --------------------------------------------------------------
printf "rule file malformed, skipped: %s\n", join(', ', @malformed) if @malformed;

my $words = 0;
my %hits;

for my $n (0 .. $#lines) {
    my $line = $lines[$n];
    next if $line =~ /^\s*$/;

    # `a = 1; b = 2` is code, not a run-on sentence. One placeholder keeps the
    # word count honest.
    $line =~ s/(`+)(?:(?!\1).)*?\1/X/gs;

    for my $rule (@res) {
        printf "line %d: %s\n", $n + 1, $rule->[1] if $line =~ $rule->[0];
    }

    # A density rule asks how often a mark appears, not whether it appears.
    # Counting runs over the whole draft, so it is reported once at the end.
    $words += grep { /\S/ } split /\s+/, $line;
    for my $d (@densities) {
        # Counting in list context returns capture groups, not matches, so a
        # rule with a group would count wrong. A loop counts matches.
        my $found = 0;
        $found++ while $line =~ /$d->[0]/g;
        $hits{ $d->[3] } += $found;
    }

    next unless $maxwords;
    # A heading, a table row, a quote and a list item are not sentences.
    next if $line =~ m{^\s*(?:[#>|]|[-*+]\s|\d+[.)]\s)};
    for my $sentence (split /(?<=[.!?])\s+/, $line) {
        my @sentence_words = grep { /\S/ } split /\s+/, $sentence;
        if (@sentence_words > $maxwords) {
            printf "line %d: %s\n", $n + 1, $maxwords_msg;
            last;
        }
    }
}

# A rate needs enough words to mean anything. One em dash in a two-line Slack
# message is not a habit, and reporting it would be noise.
if ($words >= 150) {
    for my $d (@densities) {
        my ($floor, $rate, $msg) = @{$d}[ 1, 2, 3 ];
        my $count = $hits{$msg} || 0;
        # The floor keeps one mark in a short draft from reading as a habit.
        # The rate keeps a long draft from being exempt.
        printf "draft: %s (%d in %d words)\n", $msg, $count, $words
            if $count >= $floor and $count * 1000 / $words > $rate;
    }
}
