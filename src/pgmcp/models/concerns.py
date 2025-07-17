from abc import ABC, abstractmethod
from dataclasses import dataclass


# from transitions import Machine


# class IngestionPipeline(Machine):
#     states = [
#         'new', 'job_created', 'scheduled', 'fetching', 'unstructured',
#         'structured', 'chunking', 'question_generation', 'embedding',
#         'completed', 'failed'
#     ]

#     transitions = [
#         {'trigger': 'create_job',          'source': 'new',                 'dest': 'job_created'},
#         {'trigger': 'schedule_job',        'source': 'job_created',         'dest': 'scheduled'},
#         {'trigger': 'start_fetch',         'source': 'scheduled',           'dest': 'fetching'},
#         {'trigger': 'finish_fetch',        'source': 'fetching',            'dest': 'unstructured'},
#         {'trigger': 'convert_structured',  'source': 'unstructured',        'dest': 'structured'},
#         {'trigger': 'start_chunking',      'source': 'structured',          'dest': 'chunking'},
#         {'trigger': 'finish_chunking',     'source': 'chunking',            'dest': 'question_generation'},
#         {'trigger': 'generate_embeddings', 'source': 'question_generation', 'dest': 'embedding'},
#         {'trigger': 'complete',            'source': 'embedding',           'dest': 'completed'},
#         {'trigger': 'fail',                'source': '*',                   'dest': 'failed'},
#         {'trigger': 'retry',               'source': 'failed',              'dest': 'new'},
#     ]

#     def __init__(self, job):
#         super().__init__(
#             states=IngestionPipeline.states,
#             transitions=IngestionPipeline.transitions,
#             initial=job.state
#         )
#         self.job = job
#         self.add_model(job)
