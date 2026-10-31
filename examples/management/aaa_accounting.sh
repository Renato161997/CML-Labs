#!/bin/bash
# Fresh accounting evidence for disposable, physically isolated CML guests.

add_record() {
    local user=$1 status=$2 identifier=$3
    [[ $user == viewer && $identifier =~ ^[a-zA-Z0-9_.:-]{1,80}$ ]] || return 0
    case ${status,,} in
        start) starts["$identifier"]=1 ;;
        stop) stops["$identifier"]=1 ;;
    esac
}

emit_pairs() {
    local backend=$1 identifier count=0 passed=false
    for identifier in "${!starts[@]}"; do
        [[ ${stops[$identifier]+present} ]] && count=$((count + 1))
    done
    ((count > 0)) && passed=true
    printf '{"passed":%s,"backend":"%s","completed_sessions":%s}\n' "$passed" "$backend" "$count"
    ((count > 0))
}

radius_records() {
    local line user='' status='' identifier='' key value
    local -A starts=() stops=()
    while IFS= read -r line || [[ -n $line ]]; do
        if [[ ! $line =~ [^[:space:]] ]]; then
            add_record "$user" "$status" "$identifier"
            user='' status='' identifier=''
        elif [[ $line =~ ^[[:space:]]*(User-Name|Acct-Status-Type|Acct-Session-Id)[[:space:]]*=[[:space:]]*\"?([^\"[:space:]]+) ]]; then
            key=${BASH_REMATCH[1]} value=${BASH_REMATCH[2]}
            case $key in
                User-Name) user=$value ;;
                Acct-Status-Type) status=$value ;;
                Acct-Session-Id) identifier=$value ;;
            esac
        fi
    done
    add_record "$user" "$status" "$identifier"
    emit_pairs RADIUS
}

tacacs_records() {
    local line user status identifier token
    local -a words=()
    local -A starts=() stops=()
    while IFS= read -r line || [[ -n $line ]]; do
        user='' status='' identifier=''
        read -r -a words <<< "$line"
        for token in "${words[@]}"; do
            case ${token,,} in
                viewer) user=viewer ;;
                start|stop) status=${token,,} ;;
                task_id=*) identifier=${token#*=} ;;
            esac
        done
        add_record "$user" "$status" "$identifier"
    done
    emit_pairs TACACS
}

main() {
    set -euo pipefail
    [[ $EUID == 0 && $(cat /lab/CML-AAA-FIXTURE) == CML-AAA-SESSIONS-V1 ]]
    local role action=${1:-check} file
    local -a files=()
    role=$(cat /lab/aaa-role)
    case $role in
        RADIUS)
            shopt -s nullglob
            files=(/var/log/freeradius/radacct/198.18.1.1/detail-*)
            ;;
        TACACS) [[ ! -f /tmp/cml-aaa-accounting.log ]] || files=(/tmp/cml-aaa-accounting.log) ;;
        *) return 1 ;;
    esac
    for file in "${files[@]}"; do [[ -f $file && ! -L $file ]]; done
    case $action in
        clear)
            for file in "${files[@]}"; do : > "$file"; done
            printf '{"cleared":true,"backend":"%s"}\n' "$role"
            ;;
        check)
            (for file in "${files[@]}"; do cat -- "$file"; printf '\n'; done) |
                if [[ $role == RADIUS ]]; then radius_records; else tacacs_records; fi
            ;;
        *) return 1 ;;
    esac
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main "$@"; fi
