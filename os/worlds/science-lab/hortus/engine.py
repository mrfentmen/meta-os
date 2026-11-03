"""Hortus: the Science Lab's breeding engine.

Hortus is the candidate GENERATOR inside Meta Scientia (Del's
ruling, 2026-11-01). It runs a plain genetic algorithm —
population, mutation, crossover, tournament selection — as
discrete recorded generations. Every step is a record in the
run log (records.py); the fitness of every organism comes from
the deterministic scorer in model.py. No language model is
consulted anywhere in the loop: generation here is arithmetic,
and judgement is deliberately NOT here — the verifier gate
(verifier.py) is separate code, and ladder promotion belongs to
the lab's independent verifier, not to Hortus.

A run's champion is a CANDIDATE, capped at evidence ladder
level 2 (computationally tested) and filed as a prediction
(PACK.md). Hortus output is never a discovery claim.

Determinism: one random.Random(seed) drives the whole run, so a
run is exactly reproducible from its run_start record.
"""

import random

from . import model, records as records_mod, verifier

ENGINE_NAME = "hortus"
ENGINE_VERSION = "0.1.0"
MODEL_ID = "hortus-toy-fin-v1"  # the analytic toy model in model.py

# A Hortus champion may never be filed above this ladder level.
EVIDENCE_LEVEL_CAP = 2


class Organism:
    __slots__ = ("id", "genome", "parents", "born", "score")

    def __init__(self, oid, genome, parents, born):
        self.id = oid
        self.genome = tuple(genome)
        self.parents = tuple(parents)
        self.born = born
        self.score = None


def _mutate(rng, genome, sigma_fraction=0.08, gene_bounds=None):
    child = []
    for value, (lo, hi) in zip(genome,
                               gene_bounds or model.GENE_BOUNDS):
        sigma = sigma_fraction * (hi - lo)
        child.append(min(max(value + rng.gauss(0.0, sigma), lo), hi))
    return tuple(child)


def _crossover(rng, genome_a, genome_b):
    return tuple(
        a if rng.random() < 0.5 else b
        for a, b in zip(genome_a, genome_b)
    )


def _tournament(rng, population, size=3):
    contenders = rng.sample(population, min(size, len(population)))
    return max(contenders, key=lambda org: org.score)


def _as_genome(individual):
    if isinstance(individual, Organism):
        return tuple(individual.genome)
    if isinstance(individual, dict):
        return model.parse_genome(individual.get("genome", individual))
    return model.parse_genome(individual)


def fitness(genome, env=None):
    """Deterministic fitness for one individual (the model scorer)."""
    return model.score(model.parse_genome(genome), env or model.TRAIN_ENV)


def _mutate_with_rate(rng, genome, rate, sigma_fraction=0.08,
                      gene_bounds=None):
    child = []
    for value, (lo, hi) in zip(genome,
                               gene_bounds or model.GENE_BOUNDS):
        if rng.random() < rate:
            sigma = sigma_fraction * (hi - lo)
            value = value + rng.gauss(0.0, sigma)
        child.append(min(max(value, lo), hi))
    return tuple(child)


def mutate_step(genome, seed, mutation_rate=1.0, gene_bounds=None):
    """One seeded mutation step. Rate 0 returns the genome unchanged."""
    genome = _as_genome(genome)
    rate = float(mutation_rate)
    if not 0.0 <= rate <= 1.0:
        raise ValueError("mutation_rate must be between 0 and 1")
    if rate == 0.0:
        return tuple(genome)
    return _mutate_with_rate(random.Random(seed), genome, rate,
                             gene_bounds=gene_bounds)


def breeding_step(parent_a, parent_b, seed, mutation_rate=0.0,
                  gene_bounds=None):
    """One pure breeding step: crossover, then optional mutation.

    With mutation_rate 0 every child gene comes from one of the two
    parents. Fixed parents and seed reproduce the same child.
    """
    a = _as_genome(parent_a)
    b = _as_genome(parent_b)
    if len(a) != len(b):
        raise ValueError("parents have different genome lengths")
    rate = float(mutation_rate)
    if not 0.0 <= rate <= 1.0:
        raise ValueError("mutation_rate must be between 0 and 1")
    rng = random.Random(seed)
    child = _crossover(rng, a, b)
    if rate > 0.0:
        child = _mutate_with_rate(rng, child, rate,
                                  gene_bounds=gene_bounds)
    return {
        "genome": child,
        "parent_genomes": [a, b],
        "seed": seed,
        "mutation_rate": rate,
    }


def select_parents(population, parent_count, env=None):
    """Deterministic top-score selection, capped at the requested count."""
    if not population:
        raise ValueError("select_parents refuses an empty population")
    try:
        parent_count = int(parent_count)
    except (TypeError, ValueError):
        raise ValueError("parent_count must be an integer")
    if parent_count < 0:
        raise ValueError("parent_count must be >= 0")
    scored = [(fitness(individual, env), _as_genome(individual))
              for individual in population]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [genome for _, genome in scored[:min(parent_count, len(scored))]]


def population_step(population, population_size, seed, env=None,
                    mutation_rate=0.0, elite_count=2, gene_bounds=None):
    """One pure generation step returning exactly population_size genomes.

    Elites are the top scored individuals; the rest are tournament
    selected, crossed, and optionally mutated. An empty population is
    refused with a named error.
    """
    if not population:
        raise ValueError("population_step refuses an empty population")
    try:
        population_size = int(population_size)
        elite_count = int(elite_count)
    except (TypeError, ValueError):
        raise ValueError("population_size and elite_count must be integers")
    if population_size < 1:
        raise ValueError("population_size must be >= 1")
    if elite_count < 1:
        raise ValueError("elite_count must be >= 1")
    rate = float(mutation_rate)
    if not 0.0 <= rate <= 1.0:
        raise ValueError("mutation_rate must be between 0 and 1")
    genomes = [_as_genome(individual) for individual in population]
    scored = [(fitness(genome, env), genome) for genome in genomes]
    ranked = sorted(scored, key=lambda pair: pair[0], reverse=True)
    survivors = [genome for _, genome in ranked[:min(elite_count,
                                                      population_size)]]
    rng = random.Random(seed)
    while len(survivors) < population_size:
        contenders_a = rng.sample(scored, min(3, len(scored)))
        contenders_b = rng.sample(scored, min(3, len(scored)))
        parent_a = max(contenders_a, key=lambda pair: pair[0])[1]
        parent_b = max(contenders_b, key=lambda pair: pair[0])[1]
        child = _crossover(rng, parent_a, parent_b)
        if rate > 0.0:
            child = _mutate_with_rate(rng, child, rate,
                                      gene_bounds=gene_bounds)
        survivors.append(child)
    return survivors


def run_evolution(records_path, seed=20261101, generations=300,
                  population_size=48, env=None, elite_count=2,
                  verify=True, held_out_envs=None, model_label=None,
                  gene_bounds=None):
    """Run a full evolution and write its complete record log.

    gene_bounds optionally overrides model.GENE_BOUNDS for this
    run (a wider or narrower search space); it is recorded in
    the run_start record so the log states the space it searched.
    Default None = the shipped bounds, unchanged behaviour.

    Returns a summary dict: scores at the first and last
    generation, the champion's genome and id, and the verifier
    verdict (or None when verify=False, used by tests that
    exercise the engine alone).
    """
    env = dict(env or model.TRAIN_ENV)
    bounds = tuple(
        tuple(map(float, b)) for b in (gene_bounds or model.GENE_BOUNDS))
    rng = random.Random(seed)
    writer = records_mod.RecordWriter(records_path)
    next_id = [0]

    def birth(genome, parents, born, origin):
        org = Organism(next_id[0], genome, parents, born)
        next_id[0] += 1
        writer.write("birth", organism=org.id, generation=born,
                     parents=list(parents),
                     genome=[round(g, 6) for g in genome],
                     origin=origin)
        return org

    try:
        writer.write("run_start", engine=ENGINE_NAME,
                     engine_version=ENGINE_VERSION,
                     model=model_label or MODEL_ID,
                     seed=seed, generations=generations,
                     population_size=population_size, env=env,
                     gene_bounds=[list(b) for b in bounds],
                     evidence_level_cap=EVIDENCE_LEVEL_CAP,
                     is_prediction=True)

        # Generation 0: one catalogue seed organism plus a
        # random population drawn uniformly from the bounds.
        population = [birth(model.REFERENCE_GENOME, (), 0, "seed")]
        while len(population) < population_size:
            genome = tuple(
                rng.uniform(lo, hi) for lo, hi in bounds)
            population.append(birth(genome, (), 0, "seed"))

        first_best = None
        last_best = None
        last_mean = None
        champion = None

        for gen in range(generations + 1):
            for org in population:
                org.score = model.score(org.genome, env)
            ranked = sorted(population, key=lambda o: o.score,
                            reverse=True)
            best = ranked[0]
            mean = sum(o.score for o in population) / len(population)
            writer.write("generation", generation=gen,
                         population=len(population),
                         best_score=best.score, mean_score=mean,
                         champion=best.id)
            if gen == 0:
                first_best = best.score
            last_best, last_mean, champion = best.score, mean, best
            if gen == generations:
                break

            survivors = ranked[:elite_count]
            survivor_ids = {o.id for o in survivors}
            for org in population:
                if org.id not in survivor_ids:
                    writer.write("death", organism=org.id,
                                 generation=gen,
                                 cause="not-selected")
            children = []
            while len(survivors) + len(children) < population_size:
                parent_a = _tournament(rng, population)
                parent_b = _tournament(rng, population)
                genome = _crossover(rng, parent_a.genome,
                                    parent_b.genome)
                genome = _mutate(rng, genome, gene_bounds=bounds)
                origin = ("crossover+mutation"
                          if parent_a.id != parent_b.id
                          else "mutation")
                children.append(birth(
                    genome, (parent_a.id, parent_b.id), gen + 1,
                    origin))
            population = survivors + children

        verdict = None
        if verify:
            if held_out_envs is not None:
                verdict = verifier.verify_champion(
                    champion.genome, held_out_envs=held_out_envs)
            else:
                verdict = verifier.verify_champion(champion.genome)
            writer.write("verdict", organism=champion.id,
                         genome=[round(g, 6) for g in champion.genome],
                         passed=verdict["passed"],
                         champion_status=verdict["champion_status"],
                         beat_margin=verdict["beat_margin"],
                         checks=verdict["checks"],
                         evidence_level_cap=EVIDENCE_LEVEL_CAP)

        writer.write("run_end", champion=champion.id,
                     final_population=[o.id for o in population])
    finally:
        writer.close()

    return {
        "seed": seed,
        "generations": generations,
        "population_size": population_size,
        "first_best_score": first_best,
        "final_best_score": last_best,
        "final_mean_score": last_mean,
        "champion_id": champion.id,
        "champion_genome": champion.genome,
        "verdict": verdict,
    }
