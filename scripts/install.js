#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const SKILLS = [
  "skills-governor",
  "ai-native-startup-playbook",
  "fact-driven-ai-methodology",
];

const DEFAULT_TARGETS = ["codex", "claude", "antigravity", "qoderwork", "hermes"];

const home = os.homedir();
const packageRoot = path.resolve(__dirname, "..");
const sourceRoot = path.resolve(
  process.env.GUUGO_SKILLS_SOURCE_DIR || path.join(home, ".agents", "sources", "skills", "guugo-skills"),
);
const canonicalRoot = path.resolve(
  process.env.GUUGO_SKILLS_CANONICAL_DIR || path.join(home, ".agents", "skills"),
);
const targets = (process.env.GUUGO_SKILLS_TARGETS || DEFAULT_TARGETS.join(","))
  .split(",")
  .map((target) => target.trim())
  .filter(Boolean);
const skipClients = process.env.GUUGO_SKILLS_SKIP_CLIENTS === "1";

function log(message) {
  console.log(`[guugo-skills] ${message}`);
}

function pathStat(targetPath) {
  try {
    return fs.lstatSync(targetPath);
  } catch (error) {
    if (error && error.code === "ENOENT") {
      return null;
    }
    throw error;
  }
}

function copyPath(src, dst) {
  if (!fs.existsSync(src)) {
    return;
  }
  fs.rmSync(dst, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  fs.cpSync(src, dst, { recursive: true, dereference: false });
}

function syncSourceRepository() {
  if (packageRoot === sourceRoot) {
    log(`using source repository in place: ${sourceRoot}`);
    return;
  }

  fs.mkdirSync(sourceRoot, { recursive: true });
  copyPath(path.join(packageRoot, "skills"), path.join(sourceRoot, "skills"));
  copyPath(path.join(packageRoot, "scripts"), path.join(sourceRoot, "scripts"));

  for (const file of ["README.md", "README.zh-CN.md", ".gitignore", "package.json"]) {
    copyPath(path.join(packageRoot, file), path.join(sourceRoot, file));
  }

  log(`synced source repository: ${sourceRoot}`);
}

function linkCanonicalSkills() {
  fs.mkdirSync(canonicalRoot, { recursive: true });
  const conflicts = [];

  for (const skill of SKILLS) {
    const src = path.join(sourceRoot, "skills", skill);
    const dst = path.join(canonicalRoot, skill);
    const stat = pathStat(dst);

    if (!fs.existsSync(src)) {
      throw new Error(`missing skill source: ${src}`);
    }

    if (stat && !stat.isSymbolicLink()) {
      conflicts.push(dst);
      continue;
    }

    if (stat && stat.isSymbolicLink()) {
      fs.unlinkSync(dst);
    }

    fs.symlinkSync(path.relative(canonicalRoot, src), dst);
    log(`linked ${dst}`);
  }

  if (conflicts.length > 0) {
    log("skipped existing real paths:");
    for (const conflict of conflicts) {
      log(`  ${conflict}`);
    }
  }
}

function repairClientTargets() {
  if (skipClients) {
    log("skipped client repair because GUUGO_SKILLS_SKIP_CLIENTS=1");
    return;
  }

  const doctor = path.join(sourceRoot, "skills", "skills-governor", "scripts", "skills_doctor.py");
  if (!fs.existsSync(doctor)) {
    log(`skipped client repair; missing doctor: ${doctor}`);
    return;
  }

  for (const target of targets) {
    const args = [
      doctor,
      "--source",
      canonicalRoot,
      "--target",
      target,
      "--fix",
    ];
    for (const skill of SKILLS) {
      args.push("--skill", skill);
    }

    const result = spawnSync("python3", args, { stdio: "pipe", encoding: "utf8" });
    if (result.status !== 0) {
      log(`client repair failed for ${target}: ${result.stderr || result.stdout}`.trim());
      continue;
    }
    let report = null;
    try {
      report = JSON.parse(result.stdout);
    } catch {
      // Keep a simple success message if a future doctor output is not JSON.
    }
    if (report && report.client_presence && report.client_presence.available === false) {
      log(`skipped ${target}; client not detected`);
    } else {
      log(`repaired ${target} links`);
    }
  }
}

function main() {
  log("installing reusable skills");
  syncSourceRepository();
  linkCanonicalSkills();
  repairClientTargets();
  log("done");
}

try {
  main();
} catch (error) {
  console.error(`[guugo-skills] ${error.message}`);
  process.exit(1);
}
