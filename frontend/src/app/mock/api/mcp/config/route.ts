export function GET() {
  return Response.json({
    mcp_servers: {
  "chronic-disease-his": {
    "enabled": false,
    "type": "stdio",
    "description": "Simulated diagnosis, prescriptions, tests and follow-up orders."
  },
  "medcal": {
    "enabled": false,
    "type": "stdio",
    "description": "Medical calculations and dosage conversion."
  },
  "pharmacy-operations": {
    "enabled": false,
    "type": "stdio",
    "description": "Drug catalog and inventory operations."
  }
}
  });
}
