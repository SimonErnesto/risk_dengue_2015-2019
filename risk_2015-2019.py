# -*- coding: utf-8 -*-
import numpy as np
import pymc as pm
import arviz as az
import pytensor.tensor as at
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

os.chdir(os.getcwd())


# data from Gossner et al (2022)
data = pd.read_csv("dengue_travel_europe.csv")

infected = data["infected travellers"].values.astype("int") 
total = data["total travellers"].values.astype("int")
N = len(data)

with pm.Model() as mod:
    mu_t = pm.HalfNormal("mu_t", 1)
    sd_t = pm.HalfNormal("sd_t", 1)
    mu_i = pm.HalfNormal("mu_i", 1)
    sd_i = pm.HalfNormal("sd_i", 1)
    I = pm.LogNormal("I", mu_i, sd_i, shape=N) #infected travellers
    T = pm.LogNormal("T", mu_t, sd_t, shape=N) #total travellers 
    y_i = pm.Poisson("y_i", mu=I, observed=infected)
    y_t = pm.Poisson("y_t", mu=T, observed=total)
    R = pm.Deterministic("R", 100000*I/T) #travellers rate of infection per 100000 travellers
    Ri = pm.Deterministic("Ri", (I/(T-I))*T) #raw risk (see Lee et al, 2021), i.e. ratio of infected and healthy travellers by total travellers 
    Rn = pm.Deterministic("Rn", Ri/Ri.max()) #normalised risk
    Rp = pm.Deterministic("Rp", Ri/Ri.sum()) #proportion of risk per country

dag = pm.model_to_graphviz(mod)
dag.render("model_dag", format="png")
    
with mod:
    idata = pm.sample(1000)
    
pos = idata.stack(sample = ['chain', 'draw']).posterior

az.plot_energy(idata)
plt.savefig("energy.png", dpi=300)
plt.close()

summ = az.summary(idata, hdi_prob=0.95)
summ['country'] = ["grand","grand","grand","grand"] + list(np.tile(data.country.values, 6))
summ.to_csv("summary.csv")

az.plot_trace(idata.posterior, var_names=["I", "T", "R"], kind="rank_vlines")
plt.tight_layout()
plt.savefig("rank_plots.png", dpi=300)
plt.close()

az.plot_pair(idata.posterior, var_names=["Ri"], kind=["scatter", "kde"], marginals=True)
plt.tight_layout()
plt.savefig("pair_plots_Ri.png", dpi=300)
plt.close()

az.plot_pair(idata.posterior, var_names=["Rp"], kind=["scatter", "kde"], marginals=True)
plt.tight_layout()
plt.savefig("pair_plots_Rp.png", dpi=300)
plt.close()

rph = summ[summ.index.str.contains("Rp")]
rph = rph[rph["mean"] > 0.01] #only countries with over 1% risk
rph = rph.sort_values("mean", ascending=False)
names = [rph.country[c].split(",")[0] for c in range(len(rph))]

colors = [mpl.cm.get_cmap('autumn')(x/24) for x in range(24)][:18]
fig, ax = plt.subplots()
for i in range(len(rph)):
    ax.plot((rph["hdi_2.5%"][i], rph["hdi_97.5%"][i]), (17-i, 17-i), color=colors[i])
    ax.plot(rph["mean"][i], 17-i, marker="o", markersize=5, markerfacecolor="w", color=colors[i])
    ax.set_yticks(list(np.flip(np.arange(18))), names)
    ax.spines[['right', 'top']].set_visible(False)
    ax.set_xlabel("Proportional Risk", size=12)
    ax.grid(alpha=0.5)
    ax.set_title("Countries with Hihg Proportional Risk (> 1%)")
line = mpl.lines.Line2D([], [], color='k', label='95% HDI')
circle = mpl.lines.Line2D([], [], color='w', marker='o', markeredgecolor='k', label='Posterior Mean')
ax.legend(handles=[circle, line], loc="lower right")
plt.tight_layout()    
plt.savefig("proportional_risk.png", dpi=300)
plt.close()


rs = ["R["+str(i)+"]" for i in range(99)]
rinf = summ[summ.index.isin(rs)]
fig, ax = plt.subplots(figsize=(10,15))
for i in range(len(rinf)):
    ax.plot((rinf["hdi_2.5%"][i], rinf["hdi_97.5%"][i]), (98-i, 98-i), color="k")
    ax.plot(rinf["mean"][i], 98-i, marker="o", markersize=5, markerfacecolor="w", color="k")
    ax.set_yticks(list(np.flip(np.arange(99))), rinf.country.values)
    ax.spines[['right', 'top']].set_visible(False)
    ax.set_xlabel("Infection Rate per 100,000 Passengers", size=12)
    ax.grid(alpha=0.5)
    ax.set_title("Countries Infection Rate")
line = mpl.lines.Line2D([], [], color='k', label='95% HDI')
circle = mpl.lines.Line2D([], [], color='w', marker='o', markeredgecolor='k', label='Posterior Mean')
ax.legend(handles=[circle, line])
plt.tight_layout()    
plt.savefig("infection_rate.png", dpi=300)
plt.close()



###
#drawbacks: lack of timeline, so cannot tell exposed from not exposed and time-periods
###

'''
References

Gossner CM, Fournet N, Frank C, Fernández-Martínez B, Del Manso M, Gomes Dias J, 
de Valk H. Dengue virus infections among European travellers, 2015 to 2019. 
Euro Surveill. 2022 Jan;27(2):2001937. doi: 10.2807/1560-7917

Lee H, Kim Y, Kim E, ‍Lee S, Risk Assessment of Importation and Local Transmission 
of COVID-19 in South Korea: Statistical Modeling Approach JMIR Public Health 
Surveill 2021;7(6):e26784, doi: 10.2196/26784

'''