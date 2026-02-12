# Data & ML — Common Mistakes & Anti-Patterns

Common mistakes when running the data-ml specialist. Each pattern
describes a failure mode that leads to poor ML and data pipeline decisions.

**Referenced by:** `specialist_data-ml.md`
> These patterns are **illustrative, not exhaustive**. They are a starting
> point — identify additional project-specific anti-patterns as you work.
> When a listed pattern doesn't apply to the current project, skip it.

---

## A. Data Quality

### DATA-AP-01: Training Without Profiling
**Mistake:** Starts model training without profiling the dataset for distributions, missing values, outliers, class imbalance, duplicate records, and potential biases. The model trains on garbage and produces garbage confidently.
**Why:** LLM training data is dominated by ML tutorials that start with a clean, pre-processed dataset (Iris, MNIST, Titanic). The data cleaning and profiling step is glossed over as "preprocessing" in a single code block. The model mimics this by jumping to model selection because that is where tutorials spend their attention.
**Example:**
```
DATA-01: Model Training Pipeline
1. Load the dataset from CSV
2. Split into train/test (80/20)
3. Train a gradient boosted classifier
4. Evaluate on test set
```
**Instead:** Before any model work, produce a data profile report: (1) Row count, feature count, memory usage. (2) Per-feature: type, null rate, unique count, distribution (histogram for numeric, value counts for categorical). (3) Class balance for the target variable — flag if any class is <10% of the dataset. (4) Outlier detection (IQR or z-score) for numeric features. (5) Duplicate detection (exact and near-duplicate). (6) Correlation matrix to identify redundant features. Use tools like `ydata-profiling` or `Great Expectations`. This report becomes a decision artifact that informs all downstream choices.

### DATA-AP-02: Data Leakage
**Mistake:** Test set contains information that would not be available at prediction time. Common forms: temporal leakage (using future data to predict past events), target leakage (features derived from the target variable), or entity leakage (same customer in both train and test sets with correlated records).
**Why:** The model generates a standard `train_test_split(X, y, test_size=0.2, random_state=42)` because that is the universal pattern in training data. It does not analyze whether random splitting is appropriate for the data's structure. Temporal, entity-level, and target-derived leakage are subtle and require domain understanding.
**Example:**
```
DATA-03: Data Splitting
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(
    features, target, test_size=0.2, random_state=42
)
```
(applied to a time-series fraud detection dataset where transactions from the same customer appear in both splits)
**Instead:** Choose the splitting strategy based on data structure: (1) Time-series data: use temporal splits — train on data before cutoff date, test on data after. (2) Entity-correlated data: use group splits — `GroupKFold` with customer_id as the group so the same customer never appears in both train and test. (3) Audit features for target leakage — any feature that is derived from or correlated with the target at >0.95 should be investigated. Document the splitting strategy and the reasoning in the decision.

### DATA-AP-03: Missing Feature Importance Analysis
**Mistake:** Builds models with 50+ features without analyzing which features actually contribute predictive signal. Many features add noise, increase training time, and make the model harder to interpret without improving performance.
**Why:** The model treats all available features as potentially useful because "more data is better" is a common ML heuristic in training data. Feature selection and importance analysis are presented as optional optimization steps, not as essential design decisions.
**Example:**
```
DATA-04: Feature Engineering
Include all available columns as model features:
- 47 user behavior metrics
- 12 demographic fields
- 8 derived ratios
Total: 67 features → feed all into the model
```
**Instead:** Run feature importance analysis before finalizing the feature set: (1) Train a simple model (random forest) and extract feature importances. (2) Use SHAP values for more nuanced importance. (3) Check for multicollinearity — features with >0.9 correlation provide redundant information. (4) Remove features that contribute <1% of total importance. (5) Retrain with the reduced feature set and compare metrics. Often, 10-15 features provide 95% of the predictive power. Document the top features and why they are predictive (domain interpretation, not just statistical importance).

### DATA-AP-04: No Data Versioning
**Mistake:** Trains models on datasets that change without tracking which version of the data produced which model. When model performance degrades in production, there is no way to determine if the cause is data drift, a code change, or a data pipeline bug.
**Why:** Data versioning is an MLOps concern that appears in specialized tooling documentation (DVC, MLflow, Weights & Biases) but not in mainstream ML tutorials. The model defaults to loading data from a file path or database query without version awareness.
**Example:**
```
DATA-05: Data Loading
df = pd.read_csv("data/training_data.csv")
# File is overwritten weekly by the ETL pipeline
```
**Instead:** Version every dataset used for training: (1) Use DVC (Data Version Control) to track data files alongside code in git. (2) Or store datasets in a versioned object store with naming convention: `training_data_v{N}_{date}_{hash}.parquet`. (3) Record the exact data version in every experiment's metadata. (4) Never overwrite — always create a new version. (5) Store the data lineage: which raw sources, which transformations, which filters produced this training set. This enables: reproducing any past model, debugging performance regressions, auditing for compliance.

---

## B. Model Development

### DATA-AP-05: Complexity Before Baselines
**Mistake:** Jumps to neural networks, XGBoost ensembles, or transformer-based models without establishing a simple baseline. The complex model's 87% accuracy seems impressive until you discover logistic regression achieves 85% in 10 minutes of work.
**Why:** Complex models dominate ML training data because they are more interesting to write about. Blog posts about "how I used a random forest to get 82% accuracy" do not generate engagement. The model defaults to what is frequently discussed, not what is practically appropriate as a starting point.
**Example:**
```
DATA-06: Model Architecture
Use a 3-layer neural network with attention mechanism for customer churn
prediction. Architecture: embedding layer → 2 transformer blocks →
dense layer → sigmoid output.
```
(for a structured dataset with 20 features and 50K rows)
**Instead:** Start with baselines in increasing complexity: (1) Majority class predictor (floor — any model must beat this). (2) Logistic regression or decision tree (interpretable, fast, often surprisingly competitive). (3) Random forest or gradient boosting (usually the best cost/performance ratio for structured data). (4) Only then consider neural approaches IF the simpler models plateau AND the data characteristics justify it (very large dataset, unstructured data, complex feature interactions). Document each baseline's metrics and justify why you moved to the next level of complexity.

### DATA-AP-06: Evaluation on Wrong Metric
**Mistake:** Uses accuracy as the primary metric for an imbalanced dataset. 95% accuracy on a dataset where 95% of samples are the majority class means the model learned to always predict the majority class — it has zero utility.
**Why:** Accuracy is the default metric in ML tutorials and sklearn's `.score()` method. The model reaches for the most familiar metric without analyzing whether it is appropriate for the target distribution. Training data rarely discusses metric selection as a design decision.
**Example:**
```
DATA-07: Model Evaluation
Evaluate model performance using accuracy:
accuracy = model.score(X_test, y_test)
print(f"Model accuracy: {accuracy:.2%}")  # Output: 96.3%
```
(on a fraud detection dataset where 96% of transactions are legitimate)
**Instead:** Choose metrics based on the cost of errors: (1) Balanced classes: accuracy is fine, but also report F1. (2) Imbalanced classes: use precision, recall, F1, and AUC-ROC. Specify which error is more costly — in fraud detection, a missed fraud (false negative) costs $1000+ while a flagged legitimate transaction (false positive) costs a phone call. (3) Ranking tasks: use MAP, NDCG. (4) Regression: use MAE/RMSE and also report at percentiles (P50, P90, P99). Document the business cost of each error type and choose the metric that aligns with it.

### DATA-AP-07: Overfitting Disguised as Performance
**Mistake:** Reports training set metrics as model performance, or evaluates on a test set that leaked information from the training set. The model shows 99% accuracy in evaluation but performs at 60% in production.
**Why:** The model generates evaluation code that uses the same data pipeline for training and testing without checking for leakage. Reporting training metrics is a common beginner mistake that appears in tutorial code. The model does not inherently verify that evaluation is on truly held-out data.
**Example:**
```
DATA-08: Performance Report
Training accuracy: 99.2%
Validation accuracy: 98.7%
Model is ready for production deployment.
```
(validation set is a random split of the same distribution, with no temporal or entity separation)
**Instead:** Report metrics on a truly held-out test set that was NEVER used during development: (1) Split data into train (70%), validation (15%), and test (15%) BEFORE any exploration. (2) Use validation set for hyperparameter tuning and model selection. (3) Report final metrics ONLY on the test set, and only once — repeated test-set evaluation is also a form of leakage. (4) Compare train vs test metrics — a large gap (>10 percentage points) indicates overfitting. (5) If possible, validate on data from a different time period than training to simulate real deployment conditions.

### DATA-AP-08: ML When Rules Suffice
**Mistake:** Recommends a machine learning model for a classification task that has clear, explicit, stable rules. If the business logic can be expressed as `if category in ["A", "B", "C"]: return "high_priority"`, ML adds complexity without value.
**Why:** The specialist is an ML specialist — its training data is saturated with ML solutions. When you have a hammer, everything looks like a nail. The model does not have a strong "don't use ML" signal in its training data because nobody writes papers about solving problems with if-statements.
**Example:**
```
DATA-09: Priority Classification
Train a classifier to predict ticket priority (high/medium/low) based on
ticket category, customer tier, and SLA level. Use gradient boosting
with the 3 categorical features.
```
(when the business rules are: enterprise customers = high, SLA breach = high, everything else = medium)
**Instead:** Before recommending ML, check: (1) Can the rules be explicitly stated? Ask the domain expert. (2) Are the rules stable or do they change frequently? (3) How many edge cases exist? If <20 rules cover 95% of cases, use a rule engine. (4) Is the decision auditable? Rules are transparent; ML is a black box. (5) Only use ML when: the rules are too complex to enumerate, the patterns change over time, or the input is unstructured (text, images). Document WHY ML is justified, not just what model to use.

### DATA-AP-09: No Experiment Tracking
**Mistake:** Each model training run overwrites the previous results. No record of which hyperparameters, feature sets, data versions, or random seeds produced which metrics. When a previous model was better, it cannot be reproduced.
**Why:** Experiment tracking requires specialized tooling (MLflow, W&B, Neptune) that is not part of the default data science stack. The model generates training scripts that output metrics to stdout, not to a tracking system. Tutorial code treats each run as standalone.
**Example:**
```
DATA-10: Hyperparameter Tuning
# Try different parameters manually
model = XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1)
model.fit(X_train, y_train)
print(f"F1: {f1_score(y_test, model.predict(X_test)):.4f}")
# Tweak and re-run...
```
**Instead:** Set up experiment tracking from the first training run: (1) Use MLflow, Weights & Biases, or even a simple CSV log. (2) For each run, record: timestamp, git commit hash, data version, all hyperparameters, all metrics (train and test), feature set used, and model artifact path. (3) Tag runs with experiment names for grouping. (4) Compare runs visually (metric plots across experiments). (5) Reproduce the best run by loading its exact parameters. This is not optional overhead — it is the difference between engineering and guessing.

---

## C. Bias & Operations

### DATA-AP-10: Bias Not Tested
**Mistake:** Deploys a model without checking performance across demographic groups, protected classes, or meaningful subpopulations. A model that is 85% accurate overall might be 60% accurate for a specific age group, geographic region, or language.
**Why:** Aggregate metrics are the default in ML evaluation. Training data rarely includes fairness testing as a standard step. The model reports overall accuracy because that is what every tutorial does. Bias testing requires knowing which subgroups to check, which depends on domain knowledge the model may not have.
**Example:**
```
DATA-11: Model Validation
Overall metrics:
- Accuracy: 87.3%
- F1: 0.84
- AUC-ROC: 0.91
Model meets all performance thresholds. Ready for deployment.
```
**Instead:** Evaluate metrics per subgroup before deployment: (1) Identify relevant subgroups — demographic (age, gender, location), behavioral (new vs returning users), or data-source-specific (mobile vs desktop). (2) Compute the same metrics for each subgroup. (3) Flag any subgroup where performance degrades >10% from the overall metric. (4) If significant disparity exists, investigate: is it a data quality issue (underrepresented subgroup), a feature gap (missing predictive signals for that subgroup), or a genuine model bias? (5) Document subgroup performance in the model card alongside overall metrics.

### DATA-AP-11: No Drift Monitoring
**Mistake:** Deploys a model and assumes it will maintain its training-time performance indefinitely. No monitoring for input distribution changes (data drift) or prediction accuracy changes (concept drift). The model silently degrades over weeks or months.
**Why:** Model deployment is the end of the story in training data. Tutorials end with "deploy the model" as the final step. Monitoring is an MLOps concern that exists in specialized literature but not in the mainstream ML workflow the model has learned.
**Example:**
```
DATA-12: Deployment Plan
Deploy the model as a REST API endpoint. The model file is loaded at
startup and serves predictions on incoming requests. Retrain annually
or when performance issues are reported by users.
```
**Instead:** Implement monitoring at three levels: (1) Input drift: track feature distributions (mean, variance, quantiles) in production and compare to training distributions using statistical tests (KS test, PSI). Alert when drift exceeds a threshold. (2) Prediction drift: track prediction distribution — if the model starts predicting one class much more/less frequently than expected, investigate. (3) Performance monitoring: when ground truth becomes available (delayed labels), compute actual vs predicted metrics. Set up automated retraining triggers when performance drops below a threshold.

### DATA-AP-12: Training-Serving Skew
**Mistake:** Feature engineering is implemented differently in the training pipeline (batch, pandas) and the serving pipeline (real-time, application code). Subtle differences — different null handling, different normalization, different feature ordering — cause silent model degradation in production.
**Why:** Training and serving are built by different people or at different times, using different tools. The model generates a training pipeline in a Jupyter notebook and a serving pipeline in a Flask app without ensuring they apply identical transformations. Training data treats these as separate concerns.
**Example:**
```
DATA-13: Feature Pipeline
# Training (Python/Pandas):
df["age_bucket"] = pd.cut(df["age"], bins=[0, 25, 45, 65, 100])
df["total_spend"] = df["purchases"].sum(axis=1)  # uses all historical data

# Serving (API endpoint):
age_bucket = "young" if age < 25 else "mid" if age < 45 else "senior"
total_spend = last_30_days_purchases  # different time window!
```
**Instead:** Use a single feature transformation codebase for both training and serving: (1) Define feature transformations in a shared library, not in notebooks or application code separately. (2) Use a feature store (Feast, Tecton) if the project scale justifies it. (3) For simpler projects, export sklearn pipelines or write transformation functions that operate on single records AND dataframes. (4) Add integration tests that run the same input through both pipelines and assert identical output. (5) Log feature values at serving time and compare distributions to training features as part of drift monitoring.

### DATA-AP-13: No Rollback Strategy
**Mistake:** New model deployed directly to production, replacing the previous version. If the new model performs worse on real-world data (which happens often despite test-set improvements), there is no way to revert.
**Why:** Model deployment follows the same mental model as code deployment in training data, but without the rollback infrastructure. The model generates a deployment step that replaces the current model file, not a blue-green or canary deployment. Model versioning and rollback are specialized MLOps patterns.
**Example:**
```
DATA-14: Model Update
# Deploy new model
shutil.copy("models/new_model.pkl", "models/production_model.pkl")
# Restart the API server to load the new model
```
**Instead:** Implement safe deployment for models: (1) Keep previous N model versions (at least 3) in versioned storage. (2) Use canary deployment: route 5-10% of traffic to the new model, monitor metrics for 24-48 hours, then gradually increase. (3) Define automatic rollback criteria: if error rate increases >5% or latency increases >50%, automatically revert to the previous version. (4) Shadow deployment for high-stakes models: run the new model in parallel without serving its predictions, compare to the production model's outputs. (5) Never delete the previous model until the new model has been stable in production for a defined period.

### DATA-AP-14: Feedback Loop Blindness
**Mistake:** Deploys a model whose predictions influence the data used for future training, without recognizing or mitigating the feedback loop. Recommended content gets more clicks (confirming the recommendation), rejected loan applicants never get a chance to prove creditworthiness, and the model's biases become self-reinforcing.
**Why:** Feedback loops are a systems-level concern that requires reasoning about the interaction between the model and the environment over time. Training data teaches model training as a static, one-shot process. The model does not reason about how its predictions reshape future training data.
**Example:**
```
DATA-15: Continuous Learning
Retrain the recommendation model monthly on user interaction data.
Users who click on recommended items provide positive training signal.
The model improves as it learns from more user interactions.
```
(recommended items get 10x more impressions, so they naturally get more clicks regardless of relevance)
**Instead:** Identify and mitigate feedback loops: (1) Map the data flow: does the model's output influence what data the model sees next? If yes, there is a feedback loop. (2) Use exploration: reserve 5-10% of predictions for random or diverse outputs to collect unbiased data (epsilon-greedy, Thompson sampling). (3) Use counterfactual evaluation: estimate what would have happened with different predictions (inverse propensity scoring). (4) Track diversity metrics over time — if recommendations are narrowing or predictions are converging to fewer categories, the loop is tightening. (5) Retrain on a mix of model-influenced data and independently collected data to dilute the loop effect.
