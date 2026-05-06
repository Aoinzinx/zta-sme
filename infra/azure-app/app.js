// infra/azure-app/app.js — Node.js Express demo service on Azure App Service F1
// Simulates a Nepali SME subscription/orders data API.

const express = require("express");
const app = express();

app.use(express.json());

const RECORDS = [
  {
    id: "ORD-2024-1001",
    product: "Cloud Storage 100GB",
    client: "Everest Tech Pvt",
    amount_npr: 5400,
    status: "active",
  },
  {
    id: "ORD-2024-1002",
    product: "Managed Security Basic",
    client: "Pokhara SME Solutions",
    amount_npr: 12000,
    status: "active",
  },
  {
    id: "ORD-2024-1003",
    product: "Email Hosting Pro",
    client: "Biratnagar Trade Co",
    amount_npr: 3600,
    status: "pending",
  },
];

app.get("/data", (req, res) => {
  res.json({
    service:   "Azure App Service demo",
    timestamp: new Date().toISOString(),
    records:   RECORDS,
  });
});

app.get("/health", (req, res) => res.json({ status: "ok" }));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Azure demo service listening on port ${PORT}`));
