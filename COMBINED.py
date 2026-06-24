import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Load the CSV file
all_data = pd.read_csv("Diabetes Classification 2.csv")


# Point-biserial calc (equation 1) -----------------------------------------------------------------------
def pb(factor, diagnosis):
    diagnosis_yes = []
    diagnosis_no = []

    for i in range(len(factor)):
        if diagnosis.iloc[i] == 1:
            diagnosis_yes.append(factor.iloc[i])
        else:
            diagnosis_no.append(factor.iloc[i])

    n_1 = len(diagnosis_yes)
    n_0 = len(diagnosis_no)
    n = len(factor)

    M_d = sum(diagnosis_yes) / n_1
    M_nd = sum(diagnosis_no) / n_0
    sy = np.std(factor)

    R_pb = ((M_d - M_nd) / sy) * np.sqrt((n_1 * n_0) / (n ** 2))
    return R_pb
#-------------------------------------------------------------
# correlation bar graph (for visualisation)
age_corr = pb(all_data["Age"], all_data["Diagnosis"])
bmi_corr = pb(all_data["BMI"], all_data["Diagnosis"])
chol_corr = pb(all_data["Chol"], all_data["Diagnosis"])
tg_corr = pb(all_data["TG"], all_data["Diagnosis"])
hdl_corr = pb(all_data["HDL"], all_data["Diagnosis"])
ldl_corr = pb(all_data["LDL"], all_data["Diagnosis"])
cr_corr = pb(all_data["Cr"], all_data["Diagnosis"])
bun_corr = pb(all_data["BUN"], all_data["Diagnosis"])

factor_names = ["Age", "BMI", "Chol", "TG", "HDL", "LDL", "Cr", "BUN"]
correlations = [age_corr, bmi_corr, chol_corr, tg_corr, hdl_corr, ldl_corr, cr_corr, bun_corr]

plt.figure(figsize=(10, 6))
plt.bar(factor_names, correlations)
plt.title("PB Correlation of Bloodwork Factors vs Diabetes Diagnosis")
plt.xlabel("Specific Factor")
plt.ylabel("PB Correlation Coefficient")
plt.axhline(0, color="black", linewidth=1)
plt.savefig("Correlation Analysis.png")
plt.show()
#-----------------------------------------------------------------------------
# Factor vs age graphs
def ave_age(df, factor_name, diagnosis_value):
    ages = []
    averages = []
    unique_ages = sorted(df["Age"].unique())

    for age in unique_ages:
        selected_rows = df[(df["Age"] == age) & (df["Diagnosis"] == diagnosis_value)]

        if len(selected_rows) > 0:
            average_value = selected_rows[factor_name].mean()
            ages.append(age)
            averages.append(average_value)

    return ages, averages


def graph_factors_vs_age(df):
    factors = ["BMI", "Chol", "TG", "HDL", "LDL", "Cr", "BUN"]
    y_labels = ["Average BMI", "Average Cholesterol", "Average Triglycerides", "Average HDL", "Average LDL", "Average Creatinine", "Average Blood Urea Nitrogen"]

    plt.figure(figsize=(12, 14))

    for i in range(len(factors)):
        factor = factors[i]
        y_label = y_labels[i]

        non_diabetic_ages, non_diabetic_averages = ave_age(df, factor, 0)
        diabetic_ages, diabetic_averages = ave_age(df, factor, 1)

        plt.subplot(4, 2, i + 1)
        plt.plot(non_diabetic_ages, non_diabetic_averages, color="blue", marker="o", markersize=3, label="Non-Diabetic")
        plt.plot(diabetic_ages, diabetic_averages, color="red", marker="o", markersize=3, label="Diabetic")
        plt.title(factor + " vs Age")
        plt.xlabel("Age")
        plt.ylabel(y_label)
        plt.legend()
        plt.grid(True)

    plt.tight_layout()
    plt.savefig("Factors vs Age.png", dpi=300, bbox_inches="tight")
    plt.show()


graph_factors_vs_age(all_data)

# Risk score setup
diabetic_data = all_data[all_data["Diagnosis"] == 1]
non_diabetic_data = all_data[all_data["Diagnosis"] == 0]

age_diabetic_avg = diabetic_data["Age"].mean()
age_non_diabetic_avg = non_diabetic_data["Age"].mean()

bmi_diabetic_avg = diabetic_data["BMI"].mean()
bmi_non_diabetic_avg = non_diabetic_data["BMI"].mean()

hdl_diabetic_avg = diabetic_data["HDL"].mean()
hdl_non_diabetic_avg = non_diabetic_data["HDL"].mean()

ldl_diabetic_avg = diabetic_data["LDL"].mean()
ldl_non_diabetic_avg = non_diabetic_data["LDL"].mean()

tg_diabetic_avg = diabetic_data["TG"].mean()
tg_non_diabetic_avg = non_diabetic_data["TG"].mean()

# Formula used (matches Equation (2) in the report):
# Sf = (user value - non-diabetic average) / (diabetic average - non-diabetic average)
# Negative scores are changed to 0 so a lower-risk value does not cancel out other factors.
# Scores above 1 are not capped. This lets the final risk curve move towards 100 percent.
def factor_score(user_value, risk_avg, safer_avg):
    score = (user_value - safer_avg) / (risk_avg - safer_avg)

    if score < 0:
        score = 0

    return score

#risk calculation function-----------------------------------------------------------
def risk_calculation(user_age, user_bmi, user_hdl, user_ldl, user_tg):
    age_score = factor_score(user_age, age_diabetic_avg, age_non_diabetic_avg)
    bmi_score = factor_score(user_bmi, bmi_diabetic_avg, bmi_non_diabetic_avg)
    hdl_score = factor_score(user_hdl, hdl_non_diabetic_avg, hdl_diabetic_avg)
    ldl_score = factor_score(user_ldl, ldl_diabetic_avg, ldl_non_diabetic_avg)
    tg_score = factor_score(user_tg, tg_diabetic_avg, tg_non_diabetic_avg)

    weighted_sum = age_score * age_corr + bmi_score * bmi_corr + hdl_score * hdl_corr + ldl_score * ldl_corr + tg_score * tg_corr

    risk_percentage = 100 * (1 - np.exp(-0.01 * 100 * weighted_sum))
    #from equation 3

    return risk_percentage
#---------------------------------------------------------------------------------
# Pre-compute risk_score for every row so band prevalences can be calculated
all_scores = []
for i in range(len(all_data)):
    s = risk_calculation(
        all_data["Age"].iloc[i],
        all_data["BMI"].iloc[i],
        all_data["HDL"].iloc[i],
        all_data["LDL"].iloc[i],
        all_data["TG"].iloc[i],
    )
    all_scores.append(s)
all_data["risk_score"] = all_scores

# --- Build the band counts -------------------------------------------------
band_labels = ["0-20", "20-40", "40-60", "60-80", "80-100"]
band_ranges = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]

diabetic_counts = []
non_diabetic_counts = []
prevalences = []
totals = []

for low, high in band_ranges:
    band_rows = all_data[(all_data["risk_score"] >= low) & (all_data["risk_score"] < high)]
    n_total = len(band_rows)
    n_diabetic = int(band_rows["Diagnosis"].sum())
    n_non_diabetic = n_total - n_diabetic
    prevalence = 100 * n_diabetic / n_total

    diabetic_counts.append(n_diabetic)
    non_diabetic_counts.append(n_non_diabetic)
    prevalences.append(prevalence)
    totals.append(n_total)

# --- Figure 1: Stacked bar chart of band composition -----------------------
fig, ax = plt.subplots(figsize=(10, 6))

bar_positions = np.arange(len(band_labels))
bar_width = 0.65

# Non-diabetic at the bottom, diabetic stacked on top
ax.bar(bar_positions, non_diabetic_counts, bar_width,
       label="Non-diabetic", color="#4C9F70", edgecolor="black", linewidth=0.5)
ax.bar(bar_positions, diabetic_counts, bar_width,
       bottom=non_diabetic_counts, label="Diabetic",
       color="#C0392B", edgecolor="black", linewidth=0.5)

# Annotate each bar with prevalence and total count
for i in range(len(band_labels)):
    total_height = non_diabetic_counts[i] + diabetic_counts[i]
    ax.text(bar_positions[i], total_height + 30,
            f"{prevalences[i]:.1f}%\n(n={totals[i]})",
            ha="center", va="bottom", fontsize=10, fontweight="bold")

ax.set_xticks(bar_positions)
ax.set_xticklabels(band_labels)
ax.set_xlabel("Risk score band")
ax.set_ylabel("Number of individuals")
ax.set_title("Dataset distribution across risk score bands\n(prevalence of Type-2 Diabetes annotated above each band)")
ax.legend(loc="upper left")
ax.grid(True, axis="y", alpha=0.3)
ax.set_ylim(0, max([d + nd for d, nd in zip(diabetic_counts, non_diabetic_counts)]) * 1.18)

plt.tight_layout()
plt.savefig("Band Distribution.png", dpi=300, bbox_inches="tight")
plt.show()


# --- Print verification table to confirm numbers match diagnostic ----------
print("Band verification:")
print(f"{'Band':<10}{'Total':<10}{'Diabetic':<12}{'Prevalence':<12}")
print("-" * 44)
for i in range(len(band_labels)):
    print(f"{band_labels[i]:<10}{totals[i]:<10}{diabetic_counts[i]:<12}{prevalences[i]:.1f}%")

# Assign a score to one of five fixed bands
def get_band(score):
    if score < 20:
        return "0-20"
    elif score < 40:
        return "20-40"
    elif score < 60:
        return "40-60"
    elif score < 80:
        return "60-80"
    else:
        return "80-100"

# Return the diabetes prevalence among all dataset rows that fall in the same band
def band_prevalence(band_label, df):
    band_ranges = {"0-20": (0, 20), "20-40": (20, 40), "40-60": (40, 60),
                   "60-80": (60, 80), "80-100": (80, 101)}
    low, high = band_ranges[band_label]
    band_rows = df[(df["risk_score"] >= low) & (df["risk_score"] < high)]
    n_total = len(band_rows)
    n_diabetic = int(band_rows["Diagnosis"].sum())
    prevalence = round(100 * n_diabetic / n_total, 1)
    return prevalence, n_diabetic, n_total

def boxplots_for_user(user_bmi, user_hdl, user_ldl, user_tg, df):
    diabetic     = df[df["Diagnosis"] == 1]
    non_diabetic = df[df["Diagnosis"] == 0]

    factors = {"BMI": user_bmi, "HDL": user_hdl, "LDL": user_ldl, "TG":  user_tg,}

    fig, ax = plt.subplots(4, 1, figsize=(10, 16))
    #only doing boxplots based on the age rationale in the report.

    # Week 4: iterate over the dictionary with .items().
    i = 0
    for factor, user_value in factors.items():
        a = ax[i]

        all_values = df[factor].dropna()
        diabetic_avg = diabetic[factor].mean()
        non_diabetic_avg = non_diabetic[factor].mean()

        # Week 8: boxplot. showfliers=False hides extreme outliers visually.
        a.boxplot(all_values, showfliers=False, widths=0.5)

        # Week 6: axhline for reference lines. Week 2: f-strings for labels.
        a.axhline(user_value,       color="blue",  linewidth=2,
                  label=f"Your value = {user_value:.2f}")
        a.axhline(diabetic_avg,     color="red",   linewidth=2,
                  label=f"Diabetic avg = {diabetic_avg:.2f}")
        a.axhline(non_diabetic_avg, color="green", linewidth=2,
                  label=f"Non-diabetic avg = {non_diabetic_avg:.2f}")

        # Week 6 "syntax gotchas": ax.set_* on the specific subplot.
        a.set_title(f"{factor} Distribution")
        a.set_ylabel(factor)
        a.set_xticks([1])
        a.set_xticklabels(["All Data"])
        a.legend(fontsize=8)
        a.grid(True)

        i += 1

    plt.tight_layout()
    plt.savefig("User Boxplot Comparison.png", dpi=300, bbox_inches="tight")
    plt.show()

# User inputs
print("")
print("Diabetes Risk Screening Tool")
print("-" * 35)

user_age = float(input("Enter your age: "))
user_bmi = float(input("Enter your BMI: "))
user_hdl = float(input("Enter your HDL (mmol/L): "))
user_ldl = float(input("Enter your LDL (mmol/L): "))
user_tg = float(input("Enter your triglycerides (mmol/L): "))

risk = risk_calculation(user_age, user_bmi, user_hdl, user_ldl, user_tg)

# --- Figure 2: Histogram of raw scores, coloured by diagnosis --------------
fig, ax = plt.subplots(figsize=(10, 6))

bins = np.arange(0, 102, 4)
ax.hist(all_data[all_data["Diagnosis"] == 0]["risk_score"], bins=bins,
        color="green", alpha=0.7, label="Non-diabetic", edgecolor="black", linewidth=0.3)
ax.hist(all_data[all_data["Diagnosis"] == 1]["risk_score"], bins=bins,
        color="red", alpha=0.7, label="Diabetic", edgecolor="black", linewidth=0.3)

# Mark band boundaries
for boundary in [20, 40, 60, 80]:
    ax.axvline(boundary, color="black", linestyle="--", linewidth=1, alpha=0.5)

# zorder=1 keeps the yellow line behind the band label boxes
ax.axvline(risk, color="yellow", linewidth=2.5, zorder=1)

# Label each band region — dropped to 0.82 to leave room for the score box above
y_max = ax.get_ylim()[1]
band_centres = [10, 30, 50, 70, 90]
for centre, label, prev in zip(band_centres, band_labels, prevalences):
    ax.text(centre, y_max * 0.82, f"{label}\n{prev:.1f}%",
            ha="center", va="top", fontsize=9, zorder=3,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray", alpha=0.8))

# Individual score box sits between the top border and the band labels
ax.text(risk, y_max * 0.98, f"Individual score: {risk:.1f}",
        ha="left", va="top", fontsize=9, zorder=3,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", edgecolor="gray", alpha=0.9))

ax.set_xlabel("Risk score")
ax.set_ylabel("Number of individuals")
ax.set_title("Risk score distribution by diagnosis group\n(dashed lines mark band boundaries)")
ax.legend(loc="center left")
ax.grid(True, axis="y", alpha=0.3)
ax.set_xlim(0, 100)

plt.tight_layout()
plt.savefig("Score Distribution.png", dpi=300, bbox_inches="tight")
plt.show()

boxplots_for_user(user_bmi, user_hdl, user_ldl, user_tg, all_data)

user_band = get_band(risk)
prevalence, n_diabetic, n_total = band_prevalence(user_band, all_data)

print("")
print("Results")
print("-------")
print(f"Your risk score: {risk:.1f}")
print(f"Your risk score places you in Band {user_band}.")
print(f"Of the {n_total} individuals in our dataset who fall in this band,")
print(f"{n_diabetic} ({prevalence}%) were diagnosed with Type-2 Diabetes.")
print("")
print("IMPORTANT NOTE: This tool is a screening aid only and does not replace diagnosis from a qualified medical professional.")
