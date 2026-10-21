---
type: regex
target: trace
pattern: '"name":"(?:Edit|Write|MultiEdit|NotebookEdit)"(?![\s\S]*"name":"(?:Edit|Write|MultiEdit|NotebookEdit)")[\s\S]*"name":"Bash","input":\{"command":"[^"]*(?:unittest|pytest)'
weight: 2
---
