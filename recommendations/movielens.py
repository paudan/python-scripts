import recommendations


## Get movie titles
def loadMovieLens(path='./ml-100k'):
    movies = {}
    for line in open(path + '/u.item'):
        (id, title) = line.split('|')[0:2]
        movies[id] = title
    prefs = {}
    for line in open(path + '/u.data'):
        (user, movieid, rating, ts) = line.split('\t')
        prefs.setdefault(user, {})
        prefs[user][movies[movieid]] = float(rating)
    return prefs


def main():
    prefs = loadMovieLens()
    itemsim = recommendations.calculate_similar_items(prefs, n=50)
    print (itemsim)
    print(recommendations.get_recommended_items(prefs, itemsim, '87')[0:30])


if __name__ == "__main__": main()
