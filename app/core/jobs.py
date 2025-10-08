import asyncio
from app.core.runner import RUNNER, ProcessJob

class JobManager:
    def __init__(self):
        self.runner = RUNNER

    def get(self, agent_key: str) -> ProcessJob:
        return self.runner.get(agent_key)

    def start(self, agent_key: str):
        job = self.get(agent_key)
        loop = asyncio.get_event_loop()
        loop.create_task(job.start())
        return job

    def pause(self, agent_key: str):
        self.get(agent_key).pause()

    def resume(self, agent_key: str):
        self.get(agent_key).resume()

    def stop(self, agent_key: str):
        self.get(agent_key).stop()

    def reset(self, agent_key: str):
        self.get(agent_key).reset()

JOB_MANAGER = JobManager()
