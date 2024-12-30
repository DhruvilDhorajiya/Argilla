import streamlit as st
import pandas as pd
import argilla as rg
import json

# Load CSS from external file
def apply_styles():
    with open("styles.css", "r") as f:
        css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# Initialize session state if not already initialized
def initialize_session_state():
    if "labeled_data" not in st.session_state:
        st.session_state.labeled_data = []
    if "index" not in st.session_state:
        st.session_state.index = 0
    if "selected_label" not in st.session_state:
        st.session_state.selected_label = None

# File Upload
def upload_dataset():
    uploaded_file = st.file_uploader("Upload your dataset (CSV or JSONL):", type=["csv", "jsonl"])
    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            return pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(".json"):
            try:
                return pd.read_json(uploaded_file, lines=True)
            except ValueError:
                st.error("Invalid JSONL file format.")
    return None

# Show text column to label
def label_interface(data, text_column, question_type, labels, guidelines):
    st.markdown(f"**Text to label:**")
    record = data.iloc[st.session_state.index]
    st.markdown(f"<div class='scrollable-text'>{record[text_column]}</div>", unsafe_allow_html=True)
    
    if question_type == "Label":
        st.session_state.selected_label = st.radio("Select a label:", labels, key="label_radio")
    elif question_type == "Multi-label":
        st.session_state.selected_label = []
        for label in labels:
            checkbox_key = f"multi_label_{label}"
            if checkbox_key not in st.session_state:
                st.session_state[checkbox_key] = False
            # Render the checkbox and update state
            if st.checkbox(label, key=checkbox_key):
                st.session_state.selected_label.append(label)
    elif question_type == "Rating":
        st.session_state.selected_label = st.radio("Rate the text:", [1, 2, 3, 4, 5], key="rating_radio")
    elif question_type == "Ranking":
        st.session_state.selected_label = st.text_area("Provide a ranking (comma-separated values):", key="ranking_text")
    elif question_type == "Span":
        st.session_state.selected_label = st.text_area("Provide a span annotation (start:end):", key="span_text")
    elif question_type == "Text":
        st.session_state.selected_label = st.text_area("Provide free-form text:", key="text_input")

    return st.button("Save Label", on_click=save_label, args=(data, text_column, question_type, labels, guidelines))

# Save the label for the current record
def save_label(data, text_column, question_type, labels, guidelines):
    record = data.iloc[st.session_state.index]
    st.session_state.labeled_data.append({
        "inputs": {text_column: record[text_column]},
        "annotations": st.session_state.selected_label
    })

    if question_type == "Multi-label":
        for label in labels:
            checkbox_key = f"multi_label_{label}"
            st.session_state[checkbox_key] = False
    next_record()

# Navigation between records
def next_record():
    st.session_state.index += 1
    st.session_state.selected_label = None

def previous_record():
    st.session_state.index = max(0, st.session_state.index - 1)

# Save labeled data as CSV
def save_labeled_data():
    if st.session_state.labeled_data:
        if st.button("Save labeled data"):
            labeled_df = pd.DataFrame(st.session_state.labeled_data)
            labeled_df.to_csv("labeled_data.csv", index=False)
            st.success("Labeled data saved as 'labeled_data.csv'!")

# Generate Argilla upload script
def upload_to_argilla(data, text_column, labels, question_type, guidelines):
    st.write("### Upload to Argilla")
    api_url = st.text_input("Argilla Server URL", value="https://your-argilla-server.com")
    api_key = st.text_input("Argilla API Key", type="password")
    dataset_name = st.text_input("Dataset Name", value="dataset_name")
    workspace_name = st.text_input("Workspace Name", value="default_workspace")

    if st.button("Upload to Argilla"):
        try:
            client = rg.Argilla(api_url=api_url, api_key=api_key)
            records = [
                {"text": item["inputs"][text_column], "annotations": item["annotations"]}
                for item in st.session_state.labeled_data
            ]
            
            question = None
            if question_type == "Label":
                question = rg.LabelQuestion(name="label", labels=labels)
            elif question_type == "Multi-label":
                question = rg.MultiLabelQuestion(name="multi_label", labels=labels)
            elif question_type == "Rating":
                question = rg.RatingQuestion(name="rating", values=list(range(1, 6)))
            elif question_type == "Ranking":
                question = rg.RankingQuestion(name="ranking")
            elif question_type == "Span":
                question = rg.SpanQuestion(name="span")
            elif question_type == "Text":
                question = rg.TextQuestion(name="text")

            settings = rg.Settings(
                guidelines=guidelines,
                fields=[rg.TextField(name="text", title="Text from the dataset", use_markdown=False)],
                questions=[question]
            )

            dataset = rg.Dataset(name=dataset_name, workspace=workspace_name, settings=settings)
            dataset.create()
            dataset.records.log(records=records, mapping={"text": "text"})
            st.success("Data uploaded to Argilla!")

        except Exception as e:
            st.error(f"Failed to upload to Argilla: {str(e)}")

# Main logic to drive the app
def main():
    apply_styles()
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    st.markdown('<h1>Dataset Labeling and Argilla Upload Tool</h1>', unsafe_allow_html=True)

    data = upload_dataset()
    if data is not None:
        initialize_session_state()
        st.markdown("**Select the column you want to display:**")
        text_column = st.selectbox("", data.columns)
        st.markdown("**Select question type:**")
        question_type = st.selectbox("", ["Label", "Multi-label", "Rating", "Ranking", "Span", "Text"])

        # Initialize labels only for "Label" and "Multi-label" questions
        labels = []
        if question_type in ["Label", "Multi-label"]:
            st.markdown(f"**Define possible {question_type} (comma-separated):**")
            labels = st.text_input("", value="").split(",")

        st.markdown("**Write labeling guidelines:**")
        guidelines = st.text_area("", value="Provide appropriate labels for the given data.")

        # Labeling interface
        if st.session_state.index < len(data):
            label_interface(data, text_column, question_type, labels, guidelines)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.session_state.index > 0:
                    st.button("Previous", on_click=previous_record)
            with col2:
                if st.session_state.index < len(data) - 1:
                    st.button("Next", on_click=next_record)

        else:
            st.success("Labeling complete!")

        # Save labeled data
        save_labeled_data()

        # Upload to Argilla
        upload_to_argilla(data, text_column, labels, question_type, guidelines)

    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
