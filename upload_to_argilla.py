
import streamlit as st
import pandas as pd
import argilla as rg

# Initialize Streamlit app
st.title("Dataset Labeling and Argilla Upload Tool")

# Upload dataset
uploaded_file = st.file_uploader("Upload your dataset (CSV or JSONL)", type=["csv", "jsonl"])
if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        data = pd.read_csv(uploaded_file)
    else:
        data = pd.read_json(uploaded_file, lines=True)

    # st.write("Preview of the dataset:")
    # st.dataframe(data.head())

    # User selects the column for text and defines labels dynamically
    text_column = st.selectbox("Select the column you want to display:", data.columns)
    labels = st.text_input("Define possible labels (comma-separated):").split(",")
    guidelines = st.text_area("Write labeling guidelines:", value="Provide appropriate labels for the given data.")

    # Labeling interface
    if "labeled_data" not in st.session_state:
        st.session_state.labeled_data = []
    if "index" not in st.session_state:
        st.session_state.index = 0

    def next_record():
        st.session_state.index += 1

    def previous_record():
        st.session_state.index = max(0, st.session_state.index - 1)

    if st.session_state.index < len(data):
        record = data.iloc[st.session_state.index]
        st.write("Text to label:")
        st.write(record[text_column])

        label = st.radio("Select a label:", labels)
        if st.button("Save Label"):
            st.session_state.labeled_data.append({
                "inputs": {text_column: record[text_column]},
                "annotations": [{"label": label}]
            })
            next_record()

        col1, col2 = st.columns(2)
        if st.session_state.index > 0:
            col1.button("Previous", on_click=previous_record)
        if st.session_state.index < len(data) - 1:
            col2.button("Next", on_click=next_record)

    else:
        st.write("Labeling complete!")

    # Save labeled data
    if st.session_state.labeled_data:
        if st.button("Save labeled data"):
            labeled_df = pd.DataFrame([
                {"text": item["inputs"][text_column], "label": item["annotations"][0]["label"]}
                for item in st.session_state.labeled_data
            ])
            labeled_df.to_csv("labeled_data.csv", index=False)
            st.success("Labeled data saved as 'labeled_data.csv'!")

    # Generate and execute Argilla upload script
    st.write("Upload to Argilla")
    api_url = st.text_input("Argilla Server URL", value="https://your-argilla-server.com")
    api_key = st.text_input("Argilla API Key", type="password")
    dataset_name = st.text_input("Dataset Name", value="dataset_name")
    workspace_name = st.text_input("Workspace Name", value="default_workspace")

    if st.button("Upload to Argilla"):
        client = rg.Argilla(api_url=api_url, api_key=api_key)
        records = [
            {
                "text": item["inputs"][text_column],
                "label": item["annotations"][0]["label"]
            }
            for item in st.session_state.labeled_data
        ]
        settings = rg.Settings(
            guidelines=guidelines,
            fields=[
                rg.TextField(name="text", title="Text from the dataset", use_markdown=False)
            ],
            questions=[
                rg.LabelQuestion(name="label", title="Select the appropriate label", labels=labels)
            ]
        )
        dataset = rg.Dataset(name=dataset_name, workspace=workspace_name, settings=settings)
        dataset.create()
        dataset.records.log(records=records, mapping={"text": "text"})
        st.success("Data uploaded to Argilla!")
