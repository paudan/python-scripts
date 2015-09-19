# Example from Programming Collective Intelligence, Chapter 5

import random
import math
import optimization as opt

# The dorms, each of which has two available spaces
dorms = ['Zeus', 'Athena', 'Hercules', 'Bacchus', 'Pluto']

# People, along with their first and second choices
prefs = [('Toby', ('Bacchus', 'Hercules')),
         ('Steve', ('Zeus', 'Pluto')),
         ('Karen', ('Athena', 'Zeus')),
         ('Sarah', ('Zeus', 'Pluto')),
         ('Dave', ('Athena', 'Bacchus')),
         ('Jeff', ('Hercules', 'Pluto')),
         ('Fred', ('Pluto', 'Athena')),
         ('Suzie', ('Bacchus', 'Hercules')),
         ('Laura', ('Bacchus', 'Hercules')),
         ('James', ('Hercules', 'Athena'))]

def printsolution(vec):
    slots = []
    # Create two slots for each dorm
    for i in range(len(dorms)): slots += [i, i]
    # Loop over each students assignment
    for i in range(len(vec)):
        x = int(vec[i])
        # Choose the slot from the remaining ones
        dorm = dorms[slots[x]]
        # Show the student and assigned dorm
        print prefs[i][0], dorm
        # Remove this slot
        del slots[x]


def dormcost(vec):
    cost = 0
    # Create list a of slots
    slots = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]

    # Loop over each student
    for i in range(len(vec)):
        x = int(vec[i])
        dorm = dorms[slots[x]]
        pref = prefs[i][1]
        # First choice costs 0, second choice costs 1
        if pref[0] == dorm:
            cost += 0
        elif pref[1] == dorm:
            cost += 1
        else:
            cost += 3   # Not on the list costs 3
        # Remove selected slot
        del slots[x]
    return cost


def main():
    domain = [(0, (len(dorms) * 2) - i - 1) for i in range(0, len(dorms) * 2)]
    print("Random optimization:")
    s = opt.randomoptimize(domain, dormcost)
    printsolution(s)
    print("\nSimulated annealing optimization:")
    s = opt.annealingoptimize(domain, dormcost)
    printsolution(s)
    print("\nGenetic optimization:")
    s = opt.geneticoptimize(domain, dormcost)
    printsolution(s)


if __name__ == "__main__": main()