"""
ГЕНЕТИЧЕСКИЙ ПОИСК worst-case схем для минимизации ε.
Цель: найти схему с ε → 0. Если не найдём — гипотеза усилена.
"""
import random, math, sys

def propagate(gates, fixed):
    wire = dict(fixed)
    for gtype, i1, i2, out in gates:
        v1 = wire.get(i1); v2 = wire.get(i2) if i2 >= 0 else None
        if gtype == 'AND':
            if v1 == 0 or v2 == 0: wire[out] = 0
            elif v1 is not None and v2 is not None: wire[out] = v1 & v2
        elif gtype == 'OR':
            if v1 == 1 or v2 == 1: wire[out] = 1
            elif v1 is not None and v2 is not None: wire[out] = v1 | v2
        elif gtype == 'NOT':
            if v1 is not None: wire[out] = 1 - v1
    return wire.get(gates[-1][3]) if gates else None

def sat_dfs(gates, n, max_nodes=500000):
    nodes=[0]; found=[False]
    def dfs(d, fixed):
        nodes[0]+=1
        if nodes[0]>max_nodes: return
        out=propagate(gates,fixed)
        if out is not None:
            if out==1: found[0]=True
            return
        if d>=n: return
        fixed[d]=0; dfs(d+1,fixed)
        if found[0]: return
        fixed[d]=1; dfs(d+1,fixed)
        if found[0]: return
        del fixed[d]
    dfs(0,{})
    return nodes[0] if nodes[0]<=max_nodes else None

def random_circuit(n, size):
    """Случайная схема из size гейтов."""
    gates=[]; nid=n
    for _ in range(size):
        gtype=random.choice(['AND','OR','NOT'])
        if gtype=='NOT':
            i1=random.randint(0,nid-1)
            gates.append(('NOT',i1,-1,nid))
        else:
            i1=random.randint(0,nid-1)
            i2=random.randint(0,nid-1)
            gates.append((gtype,i1,i2,nid))
        nid+=1
    return gates

def mutate_circuit(gates, n):
    """Мутация: изменяем один случайный гейт."""
    gates = list(gates)
    if not gates: return gates
    idx = random.randint(0, len(gates)-1)
    gtype, i1, i2, out = gates[idx]
    # Мутация типа
    if random.random() < 0.3:
        gtype = random.choice(['AND','OR','NOT'])
    # Мутация входов
    if random.random() < 0.5:
        i1 = random.randint(0, out-1) if out > 0 else 0
    if random.random() < 0.5 and gtype != 'NOT':
        i2 = random.randint(0, out-1) if out > 0 else 0
    if gtype == 'NOT':
        i2 = -1
    gates[idx] = (gtype, i1, i2, out)
    return gates

def evaluate_fitness(gates, n):
    """Fitness = -ε (хотим минимизировать ε)."""
    nodes = sat_dfs(gates, n, 500000)
    if nodes is None: return 0.0  # timeout = нейтральная fitness
    if nodes <= 1: return -1.0  # тривиальная схема
    eps = math.log2(max(1.01, (2**n)/nodes)) / n
    return -eps  # чем меньше ε, тем лучше fitness

def main():
    random.seed(42)
    print("=" * 60)
    print("  ГЕНЕТИЧЕСКИЙ ПОИСК worst-case схем")
    print("  Цель: минимизировать ε")
    print("=" * 60)

    n = 14
    pop_size = 40
    generations = 50
    circuit_size = 5 * n

    # Инициализация
    population = []
    for _ in range(pop_size):
        g = random_circuit(n, circuit_size)
        f = evaluate_fitness(g, n)
        population.append((g, f))

    print(f"\n  n={n}, circuit_size={circuit_size}, pop={pop_size}")
    print(f"  {'gen':>4} {'best ε':>8} {'mean ε':>8} {'worst ε':>9}")
    print(f"  {'-'*32}")

    best_ever = None; best_eps_ever = 1.0

    for gen in range(generations):
        # Сортировка (чем ниже fitness = чем меньше ε)
        population.sort(key=lambda x: x[1])

        # Лучший ε в поколении
        best_f = population[0][1]
        best_eps = -best_f if best_f < 0 else 0
        fitnesses = [-f for _, f in population if f < 0]
        mean_eps = sum(fitnesses) / len(fitnesses) if fitnesses else 0
        worst_eps = max(fitnesses) if fitnesses else 0

        if best_eps < best_eps_ever and best_eps > 0:
            best_eps_ever = best_eps
            best_ever = population[0][0]

        if gen % 5 == 0:
            print(f"  {gen:4d} {best_eps:8.4f} {mean_eps:8.4f} {worst_eps:9.4f}")
            sys.stdout.flush()

        # Селекция: лучшая половина
        survivors = population[:pop_size//2]

        # Скрещивание + мутация
        children = []
        for _ in range(pop_size//2):
            parent = random.choice(survivors)[0]
            child = mutate_circuit(parent, n)
            # Двойная мутация иногда
            if random.random() < 0.3:
                child = mutate_circuit(child, n)
            f = evaluate_fitness(child, n)
            children.append((child, f))

        population = survivors + children

    # Финальная сортировка
    population.sort(key=lambda x: x[1])
    print(f"\n  Лучший найденный ε: {best_eps_ever:.4f}")

    # Тест лучшей схемы на разных n
    if best_ever:
        print(f"\n  Верификация лучшей схемы:")
        nodes = sat_dfs(best_ever, n, 1000000)
        if nodes:
            eps = math.log2(max(1.01, (2**n)/nodes)) / n
            print(f"  n={n}: nodes={nodes}, ε={eps:.4f}")

    # Повторяем для n=16
    print(f"\n  {'='*60}")
    print(f"  Генетический поиск для n=16")

    n = 16; circuit_size = 5 * n
    population = [(random_circuit(n, circuit_size),
                    evaluate_fitness(random_circuit(n, circuit_size), n))
                   for _ in range(pop_size)]

    best_eps_16 = 1.0
    for gen in range(generations):
        population.sort(key=lambda x: x[1])
        best_f = population[0][1]
        best_eps = -best_f if best_f < 0 else 0
        if best_eps < best_eps_16 and best_eps > 0:
            best_eps_16 = best_eps
        if gen % 10 == 0:
            fitnesses = [-f for _, f in population if f < 0]
            mean_e = sum(fitnesses)/len(fitnesses) if fitnesses else 0
            print(f"  gen {gen:3d}: best ε = {best_eps:.4f}, mean = {mean_e:.4f}")
            sys.stdout.flush()

        survivors = population[:pop_size//2]
        children = []
        for _ in range(pop_size//2):
            parent = random.choice(survivors)[0]
            child = mutate_circuit(parent, n)
            if random.random() < 0.3: child = mutate_circuit(child, n)
            children.append((child, evaluate_fitness(child, n)))
        population = survivors + children

    print(f"  Лучший ε для n=16: {best_eps_16:.4f}")

    # Повторяем для n=18
    print(f"\n  {'='*60}")
    print(f"  Генетический поиск для n=18")

    n = 18; circuit_size = 5 * n
    population = [(random_circuit(n, circuit_size),
                    evaluate_fitness(random_circuit(n, circuit_size), n))
                   for _ in range(pop_size)]

    best_eps_18 = 1.0
    for gen in range(generations):
        population.sort(key=lambda x: x[1])
        best_f = population[0][1]
        best_eps = -best_f if best_f < 0 else 0
        if best_eps < best_eps_18 and best_eps > 0:
            best_eps_18 = best_eps
        if gen % 10 == 0:
            fitnesses = [-f for _, f in population if f < 0]
            mean_e = sum(fitnesses)/len(fitnesses) if fitnesses else 0
            print(f"  gen {gen:3d}: best ε = {best_eps:.4f}, mean = {mean_e:.4f}")
            sys.stdout.flush()

        survivors = population[:pop_size//2]
        children = []
        for _ in range(pop_size//2):
            parent = random.choice(survivors)[0]
            child = mutate_circuit(parent, n)
            if random.random() < 0.3: child = mutate_circuit(child, n)
            children.append((child, evaluate_fitness(child, n)))
        population = survivors + children

    print(f"  Лучший ε для n=18: {best_eps_18:.4f}")

    print(f"\n  {'='*60}")
    print(f"  ИТОГ ГЕНЕТИЧЕСКОГО ПОИСКА")
    print(f"  {'='*60}")
    print(f"  n=14: min ε = {best_eps_ever:.4f}")
    print(f"  n=16: min ε = {best_eps_16:.4f}")
    print(f"  n=18: min ε = {best_eps_18:.4f}")
    print(f"\n  Контрпример (ε ≈ 0) найден: {'ДА' if min(best_eps_ever, best_eps_16, best_eps_18) < 0.05 else 'НЕТ'}")

if __name__ == "__main__":
    main()
