# MLQ vs RM vs EDF - CPU Scheduling Comparison

Comparison of three CPU scheduling algorithms on the same set of periodic tasks:

- **MLQ** (Multilevel Queue): 3 fixed-priority queues - Q1: Round Robin (q=2), Q2: Round Robin (q=4), Q3: FCFS
- **RM** (Rate Monotonic): static priority, shorter period = higher priority
- **EDF** (Earliest Deadline First): dynamic priority, earliest deadline = higher priority

Each task has a burst time (C) and a period (T); its deadline is the end of its period.
The simulation runs over one hyperperiod. A job that misses its deadline is counted and dropped.

## Results

| Scenario | MLQ misses | RM misses | EDF misses |
|---|---|---|---|
| 1 - High load (U = 0.95) | 1 | 1 | 0 |
| 2 - Long system task in top MLQ queue (U = 0.917) | 2 | 0 | 0 |

## Comparison

| Feature | MLQ | RM | EDF |
|---|---|---|---|
| Priority | Static, by process type (queue) | Static, by period | Dynamic, by deadline |
| Used in | General-purpose OS | Real-time systems | Real-time systems |
| Deadline-aware | No | Indirectly | Yes |
| Guaranteed utilization | None | n(2^(1/n)-1) ~ 0.78 for 3 tasks | 100% |
| Weakness | Starvation of low queues | Unused CPU capacity | Unpredictable under overload |

## Files

- `compare_mlq_rm_edf.py` - simulator and comparison
- `compare_output.txt` - program output

## Run

```
python compare_mlq_rm_edf.py
```

Timeline legend: `#` = running, `.` = not running, `X` = deadline missed.
