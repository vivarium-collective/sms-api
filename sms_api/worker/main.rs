use std::{collections::HashSet, time::Duration};
use rand::Rng;
use tokio::{sync::Mutex as AsyncMutex, task, time};
use std::sync::Arc;

// Mock database connection (placeholder)
async fn connect_to_db() {
    println!("Connecting to DB...");
    // Simulate connection delay
    time::sleep(Duration::from_secs(1)).await;
    println!("Connected.");
}

// Simulate polling jobs: returns Some(job_id) or None if no jobs left
struct JobPoller {
    jobs: Vec<u32>,
    index: usize,
}

impl JobPoller {
    fn new() -> Self {
        let mut rng = rand::thread_rng();
        let jobs = (0..5).map(|_| rng.gen_range(1000..10000)).collect();
        Self { jobs, index: 0 }
    }

    async fn poll_for_jobs(&mut self) -> Option<u32> {
        if self.index < self.jobs.len() {
            let job = self.jobs[self.index];
            self.index += 1;
            Some(job)
        } else {
            None
        }
    }
}

// The CPU-bound job runner
fn run(job_id: u32) {
    println!("Processing job {}", job_id);
    let sleep_duration = rand::thread_rng().gen_range(1000..3000);
    std::thread::sleep(Duration::from_millis(sleep_duration));
    println!("Finished job {}", job_id);
    // Here, save to DB logic would go
}

// Worker loop: polls jobs, spawns blocking tasks
async fn worker_loop() {
    let mut poller = JobPoller::new();
    let seen = Arc::new(AsyncMutex::new(HashSet::new()));

    loop {
        match poller.poll_for_jobs().await {
            Some(job) => {
                let seen = seen.clone();

                // Check if already seen
                {
                    let mut s = seen.lock().await;
                    if s.contains(&job) {
                        continue;
                    }
                    s.insert(job);
                }

                // Spawn blocking job in tokio threadpool
                task::spawn_blocking(move || {
                    run(job);
                });

                // Simulate async sleep and logs like Python
                for i in 0..4 {
                    println!("Sleep {} for job: {}", i, job);
                    time::sleep(Duration::from_millis(500)).await;
                }
            }
            None => {
                println!("No more jobs. Done. Waiting.");
                // Sleep to avoid busy loop
                time::sleep(Duration::from_secs(5)).await;
            }
        }
    }
}

#[tokio::main]
async fn main() {
    connect_to_db().await;
    worker_loop().await;
}
