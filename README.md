# Intelligent Skill Gap Analysis

## Project Overview

This project is an Intelligent Skill Gap Analysis and Personalized Learning Recommendation System.

The system compares a user's resume with a target job and identifies the skills that match and the skills that are missing.

It then prioritizes the skill gaps and creates a personalized learning roadmap with learning resources.

## Project Flow

Resume
→ Resume Skill Extraction
→ Target Job Title
→ Job Description Dataset
→ Required Skill Extraction
→ ML Compatibility Prediction
→ Matched / Missing Skills
→ Skill Prioritization
→ Personalized Learning Roadmap
→ Learning Resources

## Main Features

- Resume upload
- Resume skill extraction
- Job title based job retrieval
- Resume-job skill matching
- ML based compatibility score
- Missing skill identification
- Skill gap prioritization
- Personalized learning roadmap
- Learning resource links
- Streamlit web application

## Dataset

The current job catalog contains 100,000 job records.

The dataset includes job titles, job descriptions and extracted skills.

The current catalog contains 4,178 Machine Learning Engineer records.

## Machine Learning Model

The project uses a supervised compatibility model.

The best performing model in the current experiment was:

Gradient Boosting Regressor

Current evaluation:

- MAE: 9.3385
- RMSE: 12.2061
- R²: 0.7536

The model uses features including:

- Resume skill count
- Job skill count
- Skill overlap
- TF-IDF similarity
- Semantic similarity

## Technologies Used

- Python
- Pandas
- NumPy
- Scikit-learn
- Sentence Transformers
- Joblib
- Streamlit
- TensorFlow / PyTorch related job skills
- Google Colab

## Application

The Streamlit application allows the user to upload a resume and enter a target job title.

The system then displays:

- Compatibility score
- Matched skills
- Missing skills
- Prioritized skill gaps
- Personalized learning roadmap
- Learning resources

## Current Status

The project has a working prototype and the complete basic flow has been tested using the Machine Learning Engineer role.
