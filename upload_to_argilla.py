import streamlit as st
import pandas as pd
import argilla as rg

# CSS for Enhanced UI Styling with Scroll Bar for Text and Fixed Button
st.markdown("""
    <style>
        body {
            background-color: #f9f9f9;
            font-family: 'Roboto', sans-serif;
        }
        .main-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1);
        }
        h1, h2, h3 {
            font-family: 'Roboto', sans-serif;
            color: #4CAF50;
            margin-bottom: 20px;
        }
        label {
            font-size: 16px;
            font-weight: bold;
            color: #333;
        }
        /* Specific CSS for the input fields with thinner black border */
        .stSelectbox > div, .stTextInput > div, .stTextArea > div {
            border-radius: 5px;
            border: 1px solid black;  /* Thinner black border (1px) */
            padding: 8px;
            background-color: #f9f9f9;  /* Light background color */
        }
        .stTextArea > div {
            background-color: #e8f5e9; /* Light background for text area */
            max-height: 150px;
            overflow-y: auto;  /* Scroll bar when text is too long */
        }
        .stTextInput > div {
            background-color: #e8f5e9; /* Light background for text input */
        }
        .stSelectbox > div {
            background-color: #f9f9f9; /* Light background for select box */
        }
        .button-style {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }
        .button-style:hover {
            background-color: #45a049;
        }
        .button-container {
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
        }

        /* Scrollable area for text display under "Text to label" */
        .scrollable-text {
            max-height: 200px;
            overflow-y: scroll;
            border: 1px solid #ccc;
            padding: 10px;
            margin-bottom: 10px;
            background-color: #f3f3f3;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize Streamlit app
st.markdown('<div class="main-container">', unsafe_allow_html=True)
st.markdown('<h1>Dataset Labeling and Argilla Upload Tool</h1>', unsafe_allow_html=True)

# Upload dataset
st.markdown("**Upload your dataset (CSV or JSONL):**")
uploaded_file = st.file_uploader("", type=["csv", "jsonl"])
if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        data = pd.read_csv(uploaded_file)
    else:
        data = pd.read_json(uploaded_file, lines=True)

    # Column selection with thinner black border
    st.markdown("**Select the column you want to display:**")
    text_column = st.selectbox("", data.columns)

    # Labels input field with thinner black border
    st.markdown("**Define possible labels (comma-separated):**")
    labels = st.text_input("", value="").split(",")

    # Guidelines text area with thinner black border and scroll bar
    st.markdown("**Write labeling guidelines:**")
    guidelines = st.text_area("", value="Provide appropriate labels for the given data.")
    
    # Labeling interface
    if "labeled_data" not in st.session_state:
        st.session_state.labeled_data = []
    if "index" not in st.session_state:
        st.session_state.index = 0
    if "selected_label" not in st.session_state:
        st.session_state.selected_label = None

    def next_record():
        st.session_state.index += 1
        st.session_state.selected_label = None

    def previous_record():
        st.session_state.index = max(0, st.session_state.index - 1)

    def save_label():
        record = data.iloc[st.session_state.index]
        st.session_state.labeled_data.append({
            "inputs": {text_column: record[text_column]},
            "annotations": [{"label": st.session_state.selected_label}]
        })
        next_record()

    if st.session_state.index < len(data):
        record = data.iloc[st.session_state.index]
        st.markdown("### Text to label:")
        st.markdown(f"<div class='scrollable-text'>{record[text_column]}</div>", unsafe_allow_html=True)

        # Use session state to track the selected label
        st.session_state.selected_label = st.radio("Select a label:", labels, index=0 if not st.session_state.selected_label else labels.index(st.session_state.selected_label), key="label_radio")

        # Save button triggers the save_label function
        st.button("Save Label", key="save_label", on_click=save_label)

        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.index > 0:
                st.button("Previous", key="previous_button", on_click=previous_record)
        with col2:
            if st.session_state.index < len(data) - 1:
                st.button("Next", key="next_button", on_click=next_record)

    else:
        st.success("Labeling complete!")

    # Save labeled data
    if st.session_state.labeled_data:
        if st.button("Save labeled data", key="save"):
            labeled_df = pd.DataFrame([
                {"text": item["inputs"][text_column], "label": item["annotations"][0]["label"]}
                for item in st.session_state.labeled_data
            ])
            labeled_df.to_csv("labeled_data.csv", index=False)
            st.success("Labeled data saved as 'labeled_data.csv'!")

    # Generate and execute Argilla upload script
    st.write("### Upload to Argilla")
    api_url = st.text_input("Argilla Server URL", value="https://your-argilla-server.com")
    api_key = st.text_input("Argilla API Key", type="password")
    dataset_name = st.text_input("Dataset Name", value="dataset_name")
    workspace_name = st.text_input("Workspace Name", value="default_workspace")

    if st.button("Upload to Argilla", key="upload"):
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

st.markdown('</div>', unsafe_allow_html=True)
