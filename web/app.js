const cluster = {
  term: 1,
  leader: "us-east",
  nodes: {
    "us-east": { healthy: true, log: 1 },
    "eu-west": { healthy: true, log: 1 },
    "ap-south": { healthy: true, log: 1 },
  },
  model: 17,
  tick: 21,
};

const cloudMap = {
  aws: {
    ingress: "Amazon MSK / Kinesis",
    flink: "Managed Service for Apache Flink",
    model: "EKS / SageMaker",
    batch: "S3 / EMR",
  },
  azure: {
    ingress: "Azure Event Hubs",
    flink: "Apache Flink on AKS",
    model: "AKS / Azure ML",
    batch: "ADLS Gen2 / HDInsight",
  },
  gcp: {
    ingress: "Google Cloud Pub/Sub",
    flink: "Apache Flink on GKE",
    model: "GKE / Vertex AI",
    batch: "Cloud Storage / Dataproc",
  },
};

const elements = {
  term: document.querySelector("#term"),
  health: document.querySelector("#cluster-health"),
  log: document.querySelector("#event-log"),
  fail: document.querySelector("#fail-button"),
  heal: document.querySelector("#heal-button"),
  commit: document.querySelector("#commit-button"),
};

function timestamp() {
  cluster.tick += 7 + Math.floor(Math.random() * 13);
  const seconds = Math.floor(cluster.tick / 1000);
  const millis = String(cluster.tick % 1000).padStart(3, "0");
  return `00:${String(seconds).padStart(2, "0")}.${millis}`;
}

function addEvent(message) {
  const item = document.createElement("li");
  const time = document.createElement("time");
  const body = document.createElement("p");
  time.textContent = timestamp();
  body.innerHTML = message;
  item.append(time, body);
  elements.log.prepend(item);
}

function healthyNodes() {
  return Object.entries(cluster.nodes).filter(([, node]) => node.healthy);
}

function render() {
  const healthy = healthyNodes().length;
  elements.term.textContent = cluster.term;
  elements.health.textContent = `${healthy} / 3 reachable`;
  elements.fail.disabled = !cluster.leader;
  elements.heal.disabled = healthy === 3;
  elements.commit.disabled = healthy < 2 || !cluster.leader;
  elements.commit.textContent = `Commit model v${cluster.model + 1}`;

  document.querySelectorAll(".node").forEach((element) => {
    const id = element.dataset.node;
    const node = cluster.nodes[id];
    const isLeader = cluster.leader === id;
    element.classList.toggle("leader", isLeader);
    element.classList.toggle("failed", !node.healthy);
    element.querySelector(".node-role").textContent = !node.healthy ? "ISOLATED" : isLeader ? "LEADER" : "FOLLOWER";
    element.querySelector(".node-log b").textContent = node.log;
    element.setAttribute("aria-label", `${id} ${!node.healthy ? "isolated" : isLeader ? "leader" : "follower"}, log index ${node.log}`);
  });
}

function failLeader() {
  if (!cluster.leader) return;
  const failed = cluster.leader;
  cluster.nodes[failed].healthy = false;
  cluster.leader = null;
  addEvent(`<b>${failed}</b> became unreachable; heartbeats stopped.`);

  const candidates = healthyNodes();
  if (candidates.length >= 2) {
    cluster.term += 1;
    const [winner] = candidates.sort(([nameA, nodeA], [nameB, nodeB]) => nodeB.log - nodeA.log || nameA.localeCompare(nameB));
    cluster.leader = winner;
    addEvent(`<b>${winner}</b> won term ${cluster.term} with ${candidates.length} votes.`);
  } else {
    addEvent(`Election halted: only ${candidates.length} node is reachable, below quorum.`);
  }
  render();
}

function healCluster() {
  const latest = Math.max(...Object.values(cluster.nodes).map((node) => node.log));
  Object.values(cluster.nodes).forEach((node) => {
    node.healthy = true;
    node.log = latest;
  });
  if (!cluster.leader) {
    cluster.term += 1;
    cluster.leader = "us-east";
    addEvent(`<b>us-east</b> won recovery election for term ${cluster.term}.`);
  }
  addEvent(`Recovered nodes accepted AppendEntries through index ${latest}.`);
  render();
}

function commitModel() {
  const reachable = healthyNodes();
  if (!cluster.leader || reachable.length < 2) {
    addEvent(`Rejected write: a majority is not reachable.`);
    return;
  }
  cluster.model += 1;
  const nextIndex = Math.max(...Object.values(cluster.nodes).map((node) => node.log)) + 1;
  reachable.forEach(([, node]) => { node.log = nextIndex; });
  addEvent(`Committed <code>model=v${cluster.model}</code> at index ${nextIndex} after ${reachable.length} acknowledgements.`);
  render();
}

function selectCloud(event) {
  const button = event.currentTarget;
  const services = cloudMap[button.dataset.cloud];
  document.querySelectorAll(".cloud-tabs button").forEach((tab) => {
    const selected = tab === button;
    tab.classList.toggle("active", selected);
    tab.setAttribute("aria-selected", String(selected));
  });
  document.querySelector("#ingress-service").textContent = services.ingress;
  document.querySelector("#flink-service").textContent = services.flink;
  document.querySelector("#model-service").textContent = services.model;
  document.querySelector("#batch-service").textContent = services.batch;
}

elements.fail.addEventListener("click", failLeader);
elements.heal.addEventListener("click", healCluster);
elements.commit.addEventListener("click", commitModel);
document.querySelectorAll(".cloud-tabs button").forEach((button) => button.addEventListener("click", selectCloud));
render();
