import asyncio
import threading
from app.core.runner import RUNNER, ProcessJob

class JobManager:
    def __init__(self):
        self.runner = RUNNER

    def get(self, agent_key: str) -> ProcessJob:
        return self.runner.get(agent_key)

    def start(self, agent_key: str):
        job = self.get(agent_key)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(job.start())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            threading.Thread(target=lambda: loop.run_until_complete(job.start()), daemon=True).start()
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
