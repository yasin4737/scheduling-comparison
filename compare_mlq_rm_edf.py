# مقایسه‌ی سه الگوریتم زمان‌بندی: MLQ و RM و EDF
# روی یک مجموعه‌ی مشترک از وظایف (task) دوره‌ای
from collections import deque
from math import gcd
from functools import reduce


# ---------------------------------------------------------------
# 1) تعریف وظیفه‌ها و نمونه‌های (job) آن‌ها
# ---------------------------------------------------------------
class Task:
    """وظیفه‌ی دوره‌ای: هر period واحد زمان یک job با زمان اجرای burst می‌سازد"""
    def __init__(self, name, burst, period, queue):
        self.name = name
        self.burst = burst      # زمان اجرا (C)
        self.period = period    # دوره (T) - مهلت هر job برابر پایان دوره است
        self.queue = queue      # شماره صف برای MLQ


class Job:
    """یک نمونه از وظیفه که در زمان release آزاد می‌شود"""
    def __init__(self, task, release):
        self.task = task
        self.release = release
        self.deadline = release + task.period   # مهلت مطلق
        self.remaining = task.burst
        self.finish = None

    def __repr__(self):
        return f"{self.task.name}@{self.release}"


# دو سناریوی نمونه: (نام، زمان اجرا، دوره، صف MLQ)
# سناریو 1: صف‌های MLQ به ترتیب دوره چیده شده‌اند، بار CPU بالاست
# سناریو 2: وظیفه‌ی طولانی «سیستمی» در صف 1 است (چیدمان بر اساس نوع، نه دوره)
SCENARIOS = {
    "Scenario 1 - high load (U = 0.95)": [
        ("T1", 2, 5, 1),
        ("T2", 2, 8, 2),
        ("T3", 3, 10, 3),
    ],
    "Scenario 2 - long system task in top MLQ queue": [
        ("T1", 1, 4, 2),
        ("T2", 2, 6, 3),
        ("T3", 4, 12, 1),
    ],
}


def make_tasks(spec):
    return [Task(*row) for row in spec]


# ---------------------------------------------------------------
# 2) سه سیاست زمان‌بندی
# ---------------------------------------------------------------
class RM:
    """Rate Monotonic: اولویت ثابت، دوره‌ی کوتاه‌تر = اولویت بالاتر"""
    name = "RM"

    def __init__(self):
        self.ready = []

    def add(self, job, time):
        self.ready.append(job)

    def remove(self, job):
        self.ready.remove(job)

    def select(self, current, time):
        if not self.ready:
            return None
        return min(self.ready, key=lambda j: (j.task.period, j.task.name))

    def tick(self, job):
        pass


class EDF:
    """Earliest Deadline First: اولویت پویا، مهلت نزدیک‌تر = اولویت بالاتر"""
    name = "EDF"

    def __init__(self):
        self.ready = []

    def add(self, job, time):
        self.ready.append(job)

    def remove(self, job):
        self.ready.remove(job)

    def select(self, current, time):
        if not self.ready:
            return None
        # در حالت تساوی مهلت، پردازه‌ی جاری ادامه می‌دهد (سوییچ کمتر)
        return min(self.ready,
                   key=lambda j: (j.deadline, j is not current, j.task.name))

    def tick(self, job):
        pass


class MLQ:
    """Multilevel Queue: سه صف با اولویت ثابت و قبضه‌ای بین صف‌ها"""
    name = "MLQ"
    # شماره صف -> کوانتوم (None یعنی FCFS)
    QUEUES = {1: 2, 2: 4, 3: None}

    def __init__(self):
        self.ready = {q: deque() for q in self.QUEUES}
        self.used = 0
        self.expired = None

    def add(self, job, time):
        self.ready[job.task.queue].append(job)

    def remove(self, job):
        q = self.ready[job.task.queue]
        if job in q:
            q.remove(job)
        if self.expired is job:
            self.expired = None

    def select(self, current, time):
        # کوانتوم تمام شده -> انتهای صف
        if self.expired is not None:
            q = self.ready[self.expired.task.queue]
            q.remove(self.expired)
            q.append(self.expired)
            self.expired = None
            current = None
        # صف بالاتر کار دارد -> قبضه
        if current is not None:
            higher = any(self.ready[q] for q in self.QUEUES
                         if q < current.task.queue)
            if not higher:
                return current
        for q in sorted(self.QUEUES):
            if self.ready[q]:
                job = self.ready[q][0]
                if job is not current:
                    self.used = 0
                return job
        return None

    def tick(self, job):
        self.used += 1
        quantum = self.QUEUES[job.task.queue]
        if quantum and self.used == quantum and job.remaining > 0:
            self.expired = job


# ---------------------------------------------------------------
# 3) شبیه‌ساز مشترک
# ---------------------------------------------------------------
def lcm(numbers):
    return reduce(lambda a, b: a * b // gcd(a, b), numbers)


def simulate(tasks, policy):
    """
    شبیه‌سازی واحد به واحد تا پایان ابردوره (hyperperiod).
    job ای که تا مهلتش تمام نشود، از دست رفته (miss) حساب و حذف می‌شود.
    """
    horizon = lcm([t.period for t in tasks])
    timeline = []          # نام وظیفه‌ی در حال اجرا در هر واحد زمان
    jobs, missed = [], []
    current = None
    switches = 0

    for time in range(horizon):
        # الف) حذف job هایی که مهلتشان گذشته
        for job in jobs:
            if job.finish is None and job.deadline <= time and job not in missed:
                missed.append(job)
                policy.remove(job)
                if job is current:
                    current = None
        # ب) آزاد شدن job های جدید
        for t in tasks:
            if time % t.period == 0:
                job = Job(t, time)
                jobs.append(job)
                policy.add(job, time)
        # ج) انتخاب و اجرا
        chosen = policy.select(current, time)
        if chosen is not current and chosen is not None and current is not None:
            switches += 1
        current = chosen
        if current is None:
            timeline.append(None)
            continue
        timeline.append(current.task.name)
        current.remaining -= 1
        policy.tick(current)
        if current.remaining == 0:
            current.finish = time + 1
            policy.remove(current)
            current = None

    # job هایی که در انتهای ابردوره مهلتشان رسیده
    for job in jobs:
        if job.finish is None and job.deadline <= horizon and job not in missed:
            missed.append(job)
    return horizon, timeline, jobs, missed, switches


# ---------------------------------------------------------------
# 4) چاپ نتایج
# ---------------------------------------------------------------
def print_tasks(tasks):
    print(f"{'Task':<6}{'C (burst)':<11}{'T (period)':<12}{'MLQ queue':<10}")
    print("-" * 39)
    for t in tasks:
        print(f"{t.name:<6}{t.burst:<11}{t.period:<12}{t.queue:<10}")
    n = len(tasks)
    u = sum(t.burst / t.period for t in tasks)
    bound = n * (2 ** (1 / n) - 1)
    print(f"\nCPU Utilization U = {u:.3f}")
    print(f"RM  bound n(2^(1/n)-1) = {bound:.3f} -> "
          f"{'guaranteed' if u <= bound else 'NOT guaranteed (must simulate)'}")
    print(f"EDF bound 1.000        -> "
          f"{'schedulable' if u <= 1 else 'NOT schedulable'}")


def print_timeline(tasks, horizon, timeline, missed):
    """هر سطر یک وظیفه: # = در حال اجرا، . = اجرا نمی‌شود، X = مهلت از دست رفت"""
    ruler = "".join(str(i // 10) if i % 10 == 0 else " " for i in range(horizon))
    print(f"{'':<6}{ruler}")
    for t in tasks:
        row = ["#" if timeline[i] == t.name else "." for i in range(horizon)]
        for job in missed:
            if job.task is t:
                row[job.deadline - 1] = "X"
        print(f"{t.name:<6}{''.join(row)}")


def summarize(policy_name, horizon, timeline, jobs, missed, switches):
    done = [j for j in jobs if j.finish is not None]
    resp = [j.finish - j.release for j in done]
    busy = sum(1 for x in timeline if x)
    counted = [j for j in jobs if j.deadline <= horizon]
    return {
        "name": policy_name,
        "jobs": len(counted),
        "done": len(done),
        "missed": len(missed),
        "miss%": 100 * len(missed) / len(counted),
        "resp": sum(resp) / len(resp) if resp else 0,
        "switch": switches,
        "util": 100 * busy / horizon,
        "missed_list": missed,
    }


def print_summary(results):
    print(f"{'Algorithm':<11}{'Jobs':<6}{'Done':<6}{'Missed':<8}{'Miss %':<9}"
          f"{'Avg Resp':<10}{'Switches':<10}{'CPU %':<7}")
    print("-" * 67)
    for r in results:
        print(f"{r['name']:<11}{r['jobs']:<6}{r['done']:<6}{r['missed']:<8}"
              f"{r['miss%']:<9.1f}{r['resp']:<10.2f}{r['switch']:<10}"
              f"{r['util']:<7.1f}")


# ---------------------------------------------------------------
# 5) اجرای اصلی
# ---------------------------------------------------------------
if __name__ == "__main__":
    print("=== Comparison: MLQ vs RM vs EDF ===")
    for title, spec in SCENARIOS.items():
        print("\n" + "=" * 67)
        print(title)
        print("=" * 67)
        print_tasks(make_tasks(spec))

        results = []
        for Policy in (MLQ, RM, EDF):
            tasks = make_tasks(spec)
            policy = Policy()
            horizon, timeline, jobs, missed, switches = simulate(tasks, policy)
            print(f"\n--- {policy.name} timeline (0..{horizon}) ---")
            print_timeline(tasks, horizon, timeline, missed)
            if missed:
                print("Missed deadlines:", ", ".join(
                    f"{j.task.name}(deadline {j.deadline})" for j in missed))
            else:
                print("Missed deadlines: none")
            results.append(summarize(policy.name, horizon, timeline,
                                     jobs, missed, switches))

        print(f"\n--- Summary: {title} ---")
        print_summary(results)
