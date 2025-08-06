import asyncio

from dataclasses import dataclass, field
from typing import Annotated, Any, Awaitable, Callable, Dict, Generic, List, TypeVar


T = TypeVar('T')

@dataclass
class AsyncWorkerPool(Generic[T]):
    """Generic pool of workers to process jobs concurrently.

    Usage: Create an instance of the pool and start it with a worker function.
    
    Example:
    ```
    async def worker(job_item: str) -> None:
        # Process the job item
        print(f"Processing: {job_item}")
        await asyncio.sleep(1)

    async def on_job_done(job_item: str, success: bool, message: str|None) -> None:
        # Handle job completion (e.g., logging, updating status)
        if success:
            print(f"Job {job_item} completed successfully.")
        else:
            print(f"Job {job_item} failed: {message}")
    
    pool: WorkerPool[str] = WorkerPool()
    
    for item in ["job1", "job2", "job3"]:
        await pool.add_job(item)
        
    await pool.start(worker)
    await pool.wait_for_completion()
    ```
    """
    
    # Configuration
    worker_count: int = field(default=5)
    task_timeout_seconds: int = field(default=300)
    worker: Callable[[T], Awaitable[None]] | None = field(default=None)
    on_job_done: Callable[[T, bool, str|None], Awaitable[None]] | None = field(default=None)
    on_start: Callable[[], Awaitable[None]] | None = field(default=None)
    on_complete: Callable[[], Awaitable[None]] | None = field(default=None)
    
    
    # Internal state
    jobs: asyncio.Queue[T] = field(default_factory=asyncio.Queue)
    complete: asyncio.Event = field(default_factory=asyncio.Event)
    _workers: list[asyncio.Task] = field(default_factory=list)
    _shutdown: bool = field(default=False)
    _sentinel: object = field(default_factory=object)
    
    async def start(self) -> None:
        """Start the worker pool with the given worker function."""
        self._shutdown = False
        self.complete.clear()
        
        # Validate worker function
        if not self.worker:
            raise ValueError("A worker must be defined and set in order to start the pool.")
        
        # Start worker tasks
        for _ in range(self.worker_count):
            task = asyncio.create_task(self._worker_loop())
            self._workers.append(task)
        
        # Call on_start callback if provided
        if self.on_start:
            await self.on_start()
    
    async def add_job(self, job: T) -> None:
        """Add a job to the processing queue."""
        await self.jobs.put(job)
    
    async def shutdown(self) -> None:
        """Shutdown the worker pool gracefully."""
        self._shutdown = True
        
        # Add sentinel values to wake up workers
        for _ in range(self.worker_count):
            await self.jobs.put(self._sentinel)  # type: ignore
        
        # Wait for all workers to complete
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        
        self._workers.clear()
        self.complete.set()
        
        # Call on_complete callback if provided
        if self.on_complete:
            await self.on_complete()
    
    async def wait_for_completion(self) -> None:
        """Wait for all jobs to be processed and workers to complete."""
        await self.jobs.join()
        await self.shutdown()
        await self.complete.wait()
    
    async def _worker_loop(self) -> None:
        """Internal worker loop that processes jobs from the queue."""
        while not self._shutdown:
            job = None
            try:
                # Get next job with timeout to allow periodic shutdown checks
                job = await asyncio.wait_for(self.jobs.get(), timeout=1.0)
                
                # Check for sentinel value
                if job is self._sentinel:
                    break
                
                if self.worker:
                    # Process the job with timeout
                    await asyncio.wait_for(self.worker(job), timeout=self.task_timeout_seconds)
                
                # Mark task as done
                self.jobs.task_done()
                if self.on_job_done:
                    await self.on_job_done(job, True, None)
                
            except asyncio.TimeoutError:
                # Timeout on queue get - continue to check shutdown
                continue 
            except Exception as e:
                # Log error but continue processing
                if job is not None and job is not self._sentinel:
                    self.jobs.task_done()
                    message = f"Worker error processing job {job}: {e}"
                    if self.on_job_done:
                        await self.on_job_done(job, False, message)


class AsyncWorkerPoolBase(Generic[T]):
    """A base class style usage that configures itself to use AsyncWorkerPool to call its internal work and done methods.
    
    Example:
    ```
    class MyWorker(AsyncWorkerPoolBase[str]):
        async def work_job(self, job: str) -> None:
            print(f"Processing job: {job}")
            await asyncio.sleep(1)  # Simulate work
            
        async def job_done(self, job: str, success: bool, message: str | None = None) -> None:
            if success:
                print(f"Job {job} completed successfully.")
            else:
                print(f"Job {job} failed: {message}")       
                
    pool = MyWorker(worker_count=3, task_timeout_seconds=10, jobs=["job1", "job2", "job3"])
    await pool.start()
    await pool.wait_for_completion()
    ```
    
    
    
    """
    
    
    def __init__(self, worker_count: int = 5, task_timeout_seconds: int = 300, jobs : List[T] | None = None) -> None:
        self.pool = AsyncWorkerPool[T](
            worker_count=worker_count,
            task_timeout_seconds=task_timeout_seconds,
            worker=self.work,
            on_job_done=self.done,
            on_start=self.startup,
            on_complete=self.shutdown
        )
        self._initial_jobs = jobs or []
        
    
    async def start(self) -> None:
        """Start the worker pool and add any initial jobs."""
        for job in self._initial_jobs:
            await self.pool.add_job(job)
        
        await self.pool.start()
    
    async def wait_for_completion(self) -> None:
        """Wait for all jobs to be processed and the pool to complete."""
        await self.pool.wait_for_completion()
    
    async def work(self, job: T) -> None:
        """Override this method to implement the job processing logic."""
        raise NotImplementedError("Subclasses must implement work_job method.")
    
    async def done(self, job: T, success: bool, message: str | None = None) -> None:
        """Override this method to handle job completion."""
        pass
    
    async def startup(self) -> None:
        """Override this method to handle pool startup."""
        pass
    
    async def shutdown(self) -> None:
        """Override this method to handle pool completion."""
        pass
