#!/usr/bin/env bash
# Stop hook for the writing plugin. Counts the corrections the capture hook
# logged and stays silent until one pattern has recurred. Then it surfaces that
# pattern once and asks the user where it belongs.
#
# One decision per pattern, not per correction. A one-off never recurs, so it
# never costs the user a decision.
set -uo pipefail

here=${BASH_SOURCE[0]%/*}
[[ $here == "${BASH_SOURCE[0]}" ]] && here=.
# shellcheck source=lib.sh
source "$here/lib.sh" || exit 0

payload=$(cat)

# The Stop hook fires again after it blocks. Without this the hook loops.
[[ $(jq -r '.stop_hook_active // false' <<<"$payload" 2>/dev/null) == "true" ]] && exit 0

state=$(writing_state_dir)

# A draft that is written and then deleted leaves its snapshot behind. The next
# draft at that path is a fresh start, but the stale snapshot makes the capture
# hook diff the new draft against the old one and log the whole thing as a
# correction. Those words then feed the pattern count below and invent a rule
# out of a file that was never corrected. Sweeping here rather than in the
# capture hook is what makes it work: PostToolUse fires after the write, when
# the path exists again, so only the end of the turn sees the draft gone.
for path_file in "$state"/snapshots/*.path; do
  [[ -f $path_file ]] || continue
  draft=$(cat "$path_file" 2>/dev/null)
  # An unreadable or empty sidecar proves nothing. Leave that snapshot alone.
  [[ -n $draft && ! -e $draft ]] || continue
  key=${path_file%.path}
  rm -f "$key" "$key.turn" "$path_file"
done

log=$state/corrections.jsonl
[[ -f $log ]] || exit 0

# A new rule goes where the gate will read it. The plugin's own defaults are
# the one exception: an update of the plugin replaces them, and the rule with
# them. So when the defaults are in use, the rule goes to the user's directory,
# seeded with a copy of the defaults. That directory replaces the defaults
# whole, so a lone profile file there would drop every other rule.
rules_dir=$(writing_rules_dir)
seed_from=""
if [[ $rules_dir == "$plugin_root/defaults/rules" ]]; then
  seed_from=$rules_dir
  rules_dir=$HOME/.claude/writing-line/rules
fi

# macOS still ships bash 3.2, which miscounts quotes in a heredoc inside $( ).
# An unpaired apostrophe in the text below breaks the parse there.
reason=$(/usr/bin/perl - "$log" "$state/surfaced.txt" "$rules_dir" "$seed_from" <<'PERL'
use strict;
use warnings;
use JSON::PP;

my ($log_path, $surfaced_path, $rules_dir, $seed_from) = @ARGV;

# A word that appears in every other instruction carries no signal. So do the
# verbs and nouns that show up in any request to change a draft.
my %stop = map { $_ => 1 } qw(
    about after again against all also always another any anything are because
    been before being between both came cannot come could does doing done down
    each even every from give given goes going have having here into itself
    just keep kept less like line lines little long look made make many maybe
    more most much must need needs never next none only onto other over para
    paragraph paragraphs part please rather really said same say says section
    sentence sentences should since some something still such take text than
    that their them then there these they thing things this those through
    time under until upon used using very want wants were what when where
    which while will with without word words would your yours
    add added adding change changed changes changing cut delete deleted
    draft drafts edit edited fix fixed instead move moved put remove removed
    rewrite rewrote swap tweak update updated write wrote
);

# Light stemming, so "hedging", "hedged" and "hedges" land on one key.
sub stem {
    my $w = lc shift;
    $w =~ s/[^a-z0-9]//g;
    return () if length($w) < 4;
    return () if $stop{$w};
    for my $suffix (qw(ing edly ed ly es s)) {
        if ($w =~ /\Q$suffix\E$/ and length($w) - length($suffix) >= 3) {
            $w = substr($w, 0, length($w) - length($suffix));
            last;
        }
    }
    return $w;
}

# Keyed on the pattern, not on the turn. A turn that carries two complaints
# must stay available for the second one after the first is raised.
my %surfaced;
if (open my $sf, '<', $surfaced_path) {
    while (my $key = <$sf>) { chomp $key; $surfaced{$key} = 1 if length $key }
    close $sf;
}

# Every edit in one turn answers one instruction. Collapse them, or a single
# correction that touched three files looks like three corrections.
open my $lf, '<', $log_path or exit 0;
my (%turn_reason, %turn_profile, @turn_order);
while (my $line = <$lf>) {
    my $rec = eval { decode_json($line) } or next;
    my ($id, $profile, $why) = @{$rec}{qw(prompt_id profile reason)};
    next unless defined $id and length $id;
    next unless defined $profile and length $profile;
    next unless defined $why and $why =~ /\S/;
    my $key = "$profile\t$id";
    next if exists $turn_reason{$key};
    $turn_reason{$key}  = $why;
    $turn_profile{$key} = $profile;
    push @turn_order, $key;
}
close $lf;

# A cluster is the set of turns whose instruction shares a distinctive word.
# Crude, and easy to explain back to the user, which matters more here than
# precision: the user is the classifier, the hook only decides when to ask.
my %cluster;
for my $key (@turn_order) {
    my %seen;
    for my $word (map { stem($_) } split /\s+/, $turn_reason{$key}) {
        next if $seen{$word}++;
        push @{ $cluster{ $turn_profile{$key} }{$word} }, $key;
    }
}

my $THRESHOLD = 3;
my ($best_profile, $best_word, $best_keys);
for my $profile (sort keys %cluster) {
    for my $word (sort keys %{ $cluster{$profile} }) {
        next if $surfaced{"$profile\t$word"};
        my $keys = $cluster{$profile}{$word};
        next if @$keys < $THRESHOLD;
        next if $best_keys and @$keys <= @$best_keys;
        ($best_profile, $best_word, $best_keys) = ($profile, $word, $keys);
    }
}
exit 0 unless $best_keys;

# Mark before speaking. If anything downstream fails, the worst case is a
# pattern that never gets asked about, not one that is asked about forever.
open my $sf, '>>', $surfaced_path or exit 0;
print $sf "$best_profile\t$best_word\n";
close $sf;

my $n = scalar @$best_keys;
print <<"END";
The writing plugin has $n corrections in the "$best_profile" profile that
share the same idea. The word they have in common is "$best_word".

END
print "  - $turn_reason{$_}\n" for @$best_keys;
print <<"END";

Ask the user where this belongs, using the AskUserQuestion tool. The options:

  1. A voice rule for the "$best_profile" profile. Append it to
     $rules_dir/$best_profile.md
     Put it in the Greppable block if one regex can express it, and in
     Judgment if not. If the rule holds for every profile and not just this
     one, put the Greppable half in
     $rules_dir/common.md
     instead. A Judgment bullet always stays in the profile file, even where
     it repeats another.
END
print <<"END" if length $seed_from;
     That directory does not exist yet. The rules in use are the defaults
     the plugin ships, and a plugin update replaces them. Create the
     directory by copying every file from
     $seed_from
     into it, then append there.
END
print <<"END";
  2. A reference entry, if the correction is about a term or a fact rather
     than about voice. Ask whether it holds everywhere or only in this repo,
     then write it to ~/.claude/writing-line/references/ or to
     <repo>/.claude/writing-line/references/.
  3. Discard it, if it is neither.

Write the file the user picks, then stop. This pattern will not be raised
again either way.
END
PERL
)

[[ -z $reason ]] && exit 0

jq -Rn --arg r "$reason" '{decision: "block", reason: $r}'
exit 0
