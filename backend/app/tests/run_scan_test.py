import asyncio
from app.services.agent_feature_scanner import agent_feature_scanner

async def main():
    print("Running Agent Feature Scanner diagnostic...")
    results = await agent_feature_scanner.scan_all_features()
    working = sum(1 for r in results if r["status"] == "working")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    print(f"Scan complete! Total tested: {len(results)} | Working: {working} | Skipped: {skipped}")

if __name__ == "__main__":
    asyncio.run(main())