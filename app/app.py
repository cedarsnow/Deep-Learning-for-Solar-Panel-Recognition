import gc

import streamlit as st
import cv2
import numpy as np
import torch
import albumentations as A
import segmentation_models_pytorch as smp

# ---------------------------------#
# Page layout
## Page expands to full width
st.set_page_config(
    page_title='Solar Panels Detection',
    # anatomical heart favicon
    page_icon="https://api.iconify.design/openmoji/solar-energy.svg?width=500",
    layout='wide'
)

# PAge Intro
st.write("""
# :sunny: Solar Panel Detection
Detect solar panels from satellite images in just one click!

**You could upload your own image!**
-------
""".strip())


# ---------------------------------#
# Data preprocessing and Model building

@st.cache(allow_output_mutation=True)
def imgread_preprocessing(uploaded_img):  # final preprocessing function in streamlit
    # read data
    # CLASSES = ['solar_panel']
    # class_values=[CLASSES.index(cls.lower()) for cls in classes]

    # image = cv2.imread(uploaded_img)
    image = cv2.cvtColor(uploaded_img, cv2.COLOR_BGR2RGB)
    # mask = cv2.imread(uploaded_mask,0)
    # mask = cv2.threshold(mask, 0, 255, cv2.THRESH_BINARY)[1]

    # extract certain classes from mask (e.g. cars)
    # masks = [(mask!=v) for v in class_values]
    # mask = np.stack(masks, axis=-1).astype('float')

    # add background if mask is not binary
    # if mask.shape[-1] != 1:
    #    background = 1 - mask.sum(axis=-1, keepdims=True)
    #    mask = np.concatenate((mask, background), axis=-1)

    # apply augmentations
    augmentation = get_test_augmentation()
    sample = augmentation(image=image)
    # image, mask = sample['image'], sample['mask']
    image = sample['image']

    # apply preprocessing
    preprocessing = get_preprocessing(preprocess_input)
    sample = preprocessing(image=image)
    # image, mask = sample['image'], sample['mask']
    image = sample['image']

    return image


ARCHITECTURE = smp.DeepLabV3Plus
BACKBONE = 'efficientnet-b3'
EPOCHS = 25
DEVICE='cpu'
model_path = f'./models/{ARCHITECTURE.__name__.lower()}_{BACKBONE}_model_{EPOCHS}.pth'
CLASSES = ['solar_panel']
preprocess_input = smp.encoders.get_preprocessing_fn(BACKBONE)


# sm.set_framework('tf.keras')


@st.cache(allow_output_mutation=False, ttl=24 * 60 * 60)
def get_model(model, backbone, n_classes, activation):
    return model(backbone, classes=n_classes, activation=activation)


@st.cache(allow_output_mutation=True)
def get_test_augmentation():
    """Add paddings to make image shape divisible by 32"""
    test_transform = [
        A.Resize(256, 256),
        A.PadIfNeeded(256, 256)
    ]
    return A.Compose(test_transform)

@st.cache(allow_output_mutation=True)
def to_tensor(x, **kwargs):
    return x.transpose(2, 0, 1).astype('float32')

@st.cache(allow_output_mutation=True)
def get_preprocessing(preprocessing_fn):
    """Construct preprocessing transform

    Args:
        preprocessing_fn (callbale): data normalization function
            (can be specific for each pretrained neural network)
    Return:
        transform: albumentations.Compose

    """

    _transform = [
        A.Lambda(image=preprocessing_fn),
        A.Lambda(image=to_tensor, mask=to_tensor),
    ]
    return A.Compose(_transform)


# Formatting ---------------------------------#

hide_streamlit_style = """
        <style>
        MainMenu {visibility: hidden;}
        footer {	
            visibility: hidden;
        }
        footer:after {
            content:'Created with Streamlit';
            visibility: visible;
            display: block;
            position: relative;
            #background-color: grey;
            #primary-color: blue;
            padding: 5px;
            top: 2px;
        }
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ---------------------------------#
# Sidebar - Collects user input features into dataframe
with st.sidebar.header('1. Upload your image'):
    uploaded_file = st.sidebar.file_uploader("Upload your image in png format", type=["png"])

st.sidebar.markdown("")

testfiles = ['None',
             'PV01_325206_1204151.png',
             'PV01_325206_1204186.png',
             'PV01_325574_1204564.png',
             'PV03_315173_1194612.png',
             'PV08_332400_1179443.png',
             "tile_5_18.png",
             "tile_9_4.png",
             "tile_13_8.png",
             "tile_21_10.png",


             ]

file_gts = {
    "PV01_325206_1204151" : "Zenodo",
    "PV01_325206_1204186" : "Zenodo",
    "PV01_325574_1204564" : "Zenodo",
    "PV03_315173_1194612" : "Zenodo",
    "PV08_332400_1179443" : "Zenodo",
    "tile_5_18" : 'GoogleMap',
    "tile_9_4" : 'GoogleMap',
    "tile_13_8" : 'GoogleMap',
    "tile_21_10" : 'GoogleMap',


}

if uploaded_file is None:
    with st.sidebar.header('2. Or use an image from our test set'):
        pre_trained_img = st.sidebar.selectbox(
            'Select an image',
            testfiles,
            format_func = lambda x: f'{x} ({(file_gts.get(x.replace(".png", "")))})' if ".png" in x else x,
            index = 1,
        )
        if pre_trained_img != "None":
            selected_img = "./src/data/test/" + pre_trained_img


else:
    st.sidebar.markdown("Remove the file above first to use our images.")

st.sidebar.markdown("""
###
### Developers:

- Daniel De Las Cuevas Turel
- Ricardo Chavez Torres
- Zijun He
- Sergio Aizcorbe Pardo
- Sergio Hidalgo López

""")

# ---------------------------------#
# Main panel

# define network parameters
n_classes = 1
activation = 'sigmoid'


def deploy1(uploaded_file):
    # create model
    # model = get_model(ARCHITECTURE, BACKBONE, n_classes, activation)
    model = torch.load(f'{model_path}',map_location ='cpu')
    # model = get_model(model_path)

    # st.write(uploaded_file)
    col1, col2, col3 = st.columns((0.4, 0.4, 0.2))

    with col1:  # visualize
        st.subheader('1.Visualize Image')
        with st.spinner(text="Loading the image..."):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            uploaded_file = cv2.imdecode(file_bytes, 1)
            image = cv2.resize(uploaded_file, (256, 256))

            st.image(
                image,
                caption='Image Uploaded')

    with col2:  # classify
        st.subheader('2. Model Prediction')
        with st.spinner(text="The model is running..."):
            img = imgread_preprocessing(uploaded_file)
            # image = np.expand_dims(img, axis=0)
            image = torch.from_numpy(img).to(DEVICE).unsqueeze(0)
            pr_mask = model.predict(image)
            pr_mask = (pr_mask.squeeze().numpy().round())

            st.image(pr_mask, caption='Predicted Mask')

    with col3:
        st.subheader('3. Related Data')
        st.write(
            """
            **Area predicted**:...

            **Coordinates**:...
            """
        )
    del model
    gc.collect()


def deploy2(selected_img):
    # model = sm.Unet(BACKBONE, classes=n_classes, activation=activation)
    # model.load_weights(f'{model_path}')

    # model = get_model(ARCHITECTURE, BACKBONE, n_classes, activation)
    model = torch.load(f'{model_path}',map_location ='cpu')

    col1, col2, col3 = st.columns((0.4, 0.4, 0.2))

    with col1:  # visualize
        st.subheader('1.Visualize Image')
        with st.spinner(text="Loading the image..."):
            selected_img = cv2.imread(selected_img)
            image = cv2.resize(selected_img, (256, 256))

            st.image(
                image,
                caption='Image Selected')

    with col2:  # classify
        st.subheader('2. Model Prediction')
        with st.spinner(text="The model is running..."):
            img = imgread_preprocessing(selected_img)
            # image = np.expand_dims(img, axis=0)
            image = torch.from_numpy(img).to(DEVICE).unsqueeze(0)
            pr_mask = model.predict(image)
            pr_mask = (pr_mask.squeeze().numpy().round())

            st.image(pr_mask, caption='Predicted Mask')

    with col3:
        st.subheader('3. Related Data')
        st.write(
            """
            **Area predicted**:...

            **Coordinates**:...
            """
        )

    del model
    gc.collect()


if uploaded_file is not None:
    deploy1(uploaded_file)
elif pre_trained_img != 'None':
    deploy2(selected_img)

