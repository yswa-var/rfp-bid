#!/usr/bin/env node

process.on("uncaughtException", (err) => {
  console.error(err);
  process.exit(1);
});

const cli = require("./dist");
cli.start();
