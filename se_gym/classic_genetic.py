"""
This module contains a possible genetic algorithm implementation for LLM prompt optimization, compatible with PyGAD.
"""

import typing
import openai
import pydantic
import instructor
import random

from .caller import get_format_instructions

prompt = typing.Annotated[str, "Prompt to an LLM"]


class Children(pydantic.BaseModel):
    child1: str = pydantic.Field(
        description="First child prompt. It is a combination of parent1 and parent2."
    )
    child2: str = pydantic.Field(
        description="Second child prompt. It is a combination of parent1 and parent2, but different from child1 in some way."
    )


class Child(pydantic.BaseModel):
    child: str = pydantic.Field(
        description="Child prompt. It is a mutation of its parent."
    )


CROSSOVER_SYSTEM_PROMPT = """
You are a prompt engineer. 
You are trying to improve the quality of two prompts (instructions) using a genetic algorithm by performing a crossover operation.
During the crossover operation, you combine two prompts to create two new prompts.
You are trying to maximize the fitness of the new prompts. 
The two parent prompts performed well in the previous generation, receiving fitness scores of {fitness1} and {fitness2} respectively.
To increase the fitness of the child prompts, extract the best parts of the two parent prompts and combine them in a way that improves the overall quality. 
You know that the child prompts should be similar to the parent prompts, but not identical. 
You also know that the child prompts should be different from each other.
You know the fitness scores of the parent prompts and how they are calculated.
You alway output in JSON format. 
Use the following schema: {schema} 
"""

CROSSOVER_USER_PROMPT = """
The first prompt with a fitness score of {fitness1} is:
=======================================================
{parent1}
=======================================================

The second prompt with a fitness score of {fitness2} is:
=======================================================
{parent2}
=======================================================

Based on the parent prompts, create two new prompts that are similar to the parent prompts but not identical.
"""

MUTATION_SYSTEM_PROMPT = """
You are a prompt engineer.
You are trying to improve the quality of a prompt (instructions) using a genetic algorithm by performing a mutation operation.
During the mutation operation, you modify the prompt to create a new prompt.
You are trying to maximize the fitness of the new prompt.
The parent prompt performed not so well in the previous generation, receiving a fitness score of {fitness}.
To increase the fitness of the child prompt, make major changes to the parent prompt that improve the overall quality.
You know that the child prompt should be similar to the parent prompt, but not identical.
You know the fitness score of the parent prompt and how it is calculated.
You always output in JSON format.
Use the following schema: {schema}
"""

MUTATION_USER_PROMPT = """
The parent prompt with a fitness score of {fitness} is:
=======================================================
{parent}
=======================================================
Based on the parent prompt, create a new prompt that is similar to the parent prompt but not identical.
"""


def get_messages(system_prompt, user_prompt):
    return [
        dict(role="system", content=system_prompt),
        dict(role="user", content=user_prompt),
    ]


class Population:
    def __init__(
        self,
        client: openai.Client,
        initial_individual: typing.List[prompt],
        elite_size: int = 1,
        mutation_probability: float = 0.2,
        crossover_probability: float = 0.7,
    ):
        self.client = instructor.patch(client, mode=instructor.Mode.JSON)
        self.individuals = initial_individual
        self.elite_size = elite_size
        self.mutation_probability = mutation_probability
        self.crossover_probability = crossover_probability

    def mutate(self, parent: prompt, fitness: float):
        schema = get_format_instructions(Child)
        resp = self.client.chat.completions.create(
            model="llama3:8b",
            messages=get_messages(
                MUTATION_SYSTEM_PROMPT.format(fitness=fitness, schema=schema),
                MUTATION_USER_PROMPT.format(fitness=fitness, parent=parent),
            ),
            response_model=Child,
            max_retries=1,
        )
        return resp

    def crossover(
        self, parent1: prompt, parent2: prompt, fitness1: float, fitness2: float
    ):
        schema = get_format_instructions(Children)

        resp = self.client.chat.completions.create(
            model="llama3:8b",
            messages=get_messages(
                CROSSOVER_SYSTEM_PROMPT.format(
                    fitness1=fitness1, fitness2=fitness2, schema=schema
                ),
                CROSSOVER_USER_PROMPT.format(
                    fitness1=fitness1,
                    fitness2=fitness2,
                    parent1=parent1,
                    parent2=parent2,
                ),
            ),
            response_model=Children,
            max_retries=1,
        )
        return resp

    def selection(
        self,
        fitnesses: typing.List[float],
    ):
        sorted_population = sorted(
            zip(self.individuals, fitnesses), key=lambda x: x[1], reverse=True
        )  # Select the best performing individuals
        elite = [x[0] for x in sorted_population[: self.elite_size]]  # select the elite
        mutated = []  # run mutation on mutation_probability
        for ind, fit in sorted_population:
            if ind not in elite and random.random() < self.mutation_probability:
                mutated.append(self.mutate(ind, fit))
        crossed = []  # run crossover on crossover_probability
        for i in range(0, len(sorted_population), 2):
            if random.random() < self.crossover_probability:
                crossed.append(
                    self.crossover(
                        sorted_population[i][0],
                        sorted_population[i + 1][0],
                        sorted_population[i][1],
                        sorted_population[i + 1][1],
                    )
                )
        # create new population by combining elite, mutated and crossed and fill the rest with random individuals
        new_population = (
            elite
            + [m.child for m in mutated]
            + [c.child1 for c in crossed]
            + [c.child2 for c in crossed]
        )
        while len(new_population) < len(self.individuals):
            new_population.append(random.choice(self.individuals))
        self.individuals = new_population  # update the population
