# Define Agent class
class Agent:
    def __init__(self, name):
        self.name = name
        self.memory = []

    def analyze(self, data):
        if not data:
            print(f"{self.name}: No data to analyze!")
            return None
        result = sum(data) / len(data)
        self.memory.append(result)
        print(f"{self.name} analyzed data: {result}")
        return result

# Define Manager class
class Manager:
    def __init__(self):
        self.agents = []

    def add_agent(self, agent):
        self.agents.append(agent)
        print(f"Agent {agent.name} added.")

    def run_all(self, data):
        results = []
        for agent in self.agents:
            result = agent.analyze(data)
            results.append(result)
        return results

# --- Main Execution ---

if __name__ == "__main__":   # ensures this runs when script executed
    # Create agents
    agent1 = Agent("Alpha")
    agent2 = Agent("Beta")

    # Create manager
    manager = Manager()

    # Add agents
    manager.add_agent(agent1)
    manager.add_agent(agent2)

    # Some data
    data = [10, 20, 30, 40, 50]

    # Run all agents
    results = manager.run_all(data)

    print("Final results:", results)
