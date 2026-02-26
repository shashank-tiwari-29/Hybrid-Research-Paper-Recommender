import matplotlib.pyplot as plt

def generate_year_chart(papers):
    years = [p['year'] for p in papers]
    plt.hist(years)
    plt.xlabel("Year")
    plt.ylabel("Number of Papers")
    plt.savefig("static/year_distribution.png")