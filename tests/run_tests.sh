#!/bin/sh
# The tests: tests/<name>.py run by plainpy - in the interpreter and compiled
# (plainpy --compile) - must print tests/expected/<name>.out (stdout+stderr,
# plus "[exit N]" when N != 0); expected/<name>.<target>.out, when present,
# is the expectation for that target instead.
#
# Environment:
#   PLAINPY  plainpy            (default: plainpy on the PATH)
#   TARGET   interp: the interpreter; linux, macos, kolibri: compiled for that
#            target (default: the machine's - macos on a Mac, linux elsewhere).
#            Tests named *_kolibri run only for kolibri, which needs RUN: the
#            KolibriOS emulator of plainpy's tests (python3 tests/x86run.py)
#   RUN      prefix for running the compiled programs (an emulator)
#   FASM     fasm executable    (default fasm; linux and kolibri)
#   OUT      scratch directory  (default build/tests)
#   UPDATE=1 rewrite the expected files from the current results
#
# usage: sh tests/run_tests.sh [tests/name.py ...]
PLAINPY=${PLAINPY:-plainpy}
FASM=${FASM:-fasm}
if [ -z "$TARGET" ]; then
    case "$(uname -s)" in Darwin) TARGET=macos;; *) TARGET=linux;; esac
fi
OUT=${OUT:-build/tests}
DIR=tests
EXP=$DIR/expected
# the libraries (kui, kgfx ...) and the programs' packages (nectar ...)
export PLAINPYPATH="lib:apps/nectar${PLAINPYPATH:+:$PLAINPYPATH}"
mkdir -p "$OUT" "$EXP"
pass=0; fail=0; failed=""
files="$*"
[ -n "$files" ] || files=$(ls $DIR/*.py)
for f in $files; do
    n=$(basename "$f" .py)
    case "$n" in
    *_kolibri) [ "$TARGET" = kolibri ] && [ -n "$RUN" ] || continue;;
    esac
    inp=/dev/null; [ -f "$DIR/$n.in" ] && inp="$DIR/$n.in"
    if [ "$TARGET" = interp ]; then
        "$PLAINPY" "$f" <"$inp" >"$OUT/$n.raw" 2>&1
        rc=$?
        # (a compiled program reports only the last line of an uncaught exception)
        awk '/^Traceback \(most recent call last\):$/ { tb=1; next } tb && /^  / { next } { tb=0; print }' "$OUT/$n.raw" >"$OUT/$n.got"
    else
        if ! "$PLAINPY" --compile --target "$TARGET" --fasm "$FASM" "$f" -o "$OUT/$n" >"$OUT/$n.log" 2>&1; then
            fail=$((fail+1)); failed="$failed $n"; echo "FAIL $n (does not compile)"; head -10 "$OUT/$n.log"; continue
        fi
        ev=1,3; [ -f "$DIR/$n.events" ] && ev=$(cat "$DIR/$n.events")   # scripted GUI events for the emulator
        X86RUN_EVENTS="$ev" $RUN "$OUT/$n" <"$inp" >"$OUT/$n.got" 2>&1
        rc=$?
    fi
    [ $rc -ne 0 ] && echo "[exit $rc]" >>"$OUT/$n.got"
    t=$TARGET; [ "$t" = interp ] && t=macos
    exp="$EXP/$n.out"; [ -f "$EXP/$n.$t.out" ] && exp="$EXP/$n.$t.out"
    if [ "$UPDATE" = 1 ]; then cp "$OUT/$n.got" "$exp"; fi
    if cmp -s "$OUT/$n.got" "$exp"; then pass=$((pass+1))
    else fail=$((fail+1)); failed="$failed $n"; echo "FAIL $n"; diff "$exp" "$OUT/$n.got" | head -20; fi
done
echo "tests ($TARGET): $pass passed, $fail failed"
[ $fail -eq 0 ] || { echo "failed:$failed"; exit 1; }
