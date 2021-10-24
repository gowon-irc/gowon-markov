#!/usr/bin/env sh

if [[ "${#@}" -eq 0 ]]; then
    echo "Usage: ${0} FILE"
    exit 1
fi

F="${1}"

POD=$(kubectl get po -l app.kubernetes.io/name=markov -o jsonpath="{.items[0].metadata.name}" -A)

kubectl cp "${F}" "${POD}:/data/corpus.txt" -c init-file-wait
