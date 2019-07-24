from __future__ import print_function, division
import numpy as np
import cv2
import os


def getRangImageDepth(image_src, fixedvalue=255):
    """
    :param image:
    :return:rang of image depth
    """
    # startposition, endposition = np.where(image)[0][[0, -1]]
    image = image_src.copy()
    image[image_src == fixedvalue] = 255
    image[image_src != fixedvalue] = 0
    fistflag = True
    startposition = 0
    endposition = 0
    for z in range(image.shape[0]):
        notzeroflag = np.max(image[z, :, :])
        if notzeroflag and fistflag:
            startposition = z
            fistflag = False
        if notzeroflag:
            endposition = z
    return startposition, endposition


def subimage_generator(image, patch_block_size, numberxy, numberz):
    """
    generate the sub images with patch_block_size
    :param image:
    :param patch_block_size:
    :param stride:
    :return:
    """
    width = np.shape(image)[1]
    height = np.shape(image)[2]
    imagez = np.shape(image)[0]
    block_width = np.array(patch_block_size)[1]
    block_height = np.array(patch_block_size)[2]
    blockz = np.array(patch_block_size)[0]

    stridewidth = (width - block_width) // (numberxy - 1)
    strideheight = (height - block_height) // (numberxy - 1)
    fix_stridez = numberz
    stridez = (imagez - blockz) // fix_stridez
    # step 1:if image size of z is smaller than blockz,return zeros samples
    if imagez < blockz:
        nb_sub_images = numberxy * numberxy * 1
        hr_samples = np.zeros(shape=(nb_sub_images, blockz, block_width, block_height), dtype=np.float32)
        indx = 0
        for x in range(0, width - block_width + 1, stridewidth):
            for y in range(0, height - block_height + 1, strideheight):
                hr_samples[indx, 0:imagez, :, :] = image[:, x:x + block_width, y:y + block_height]
                indx += 1
        if (indx != nb_sub_images):
            print(indx)
            print(nb_sub_images)
            raise ValueError("error sub number image")
        return hr_samples
    # step 2:if stridez is bigger 1,return  numberxy * numberxy * numberz samples
    if stridez >= 1:
        nb_sub_images = numberxy * numberxy * (stridez + 1)
        hr_samples = np.empty(shape=(nb_sub_images, blockz, block_width, block_height), dtype=np.float32)
        indx = 0
        for z in range(0, fix_stridez * (stridez + 1), fix_stridez):
            for x in range(0, width - block_width + 1, stridewidth):
                for y in range(0, height - block_height + 1, strideheight):
                    hr_samples[indx, :, :, :] = image[z:z + blockz, x:x + block_width, y:y + block_height]
                    indx += 1

        if (indx != nb_sub_images):
            print(indx)
            print(nb_sub_images)
            raise ValueError("error sub number image")
        return hr_samples

    # step3: if stridez==imagez,return numberxy * numberxy * 1 samples,one is [0:blockz,:,:]
    if imagez == blockz:
        nb_sub_images = numberxy * numberxy * 1
        hr_samples = np.empty(shape=(nb_sub_images, blockz, block_width, block_height), dtype=np.float32)
        indx = 0
        for x in range(0, width - block_width + 1, stridewidth):
            for y in range(0, height - block_height + 1, strideheight):
                hr_samples[indx, :, :, :] = image[:, x:x + block_width, y:y + block_height]
                indx += 1
        if (indx != nb_sub_images):
            print(indx)
            print(nb_sub_images)
            raise ValueError("error sub number image")
        return hr_samples
    # step4: if stridez==0,return numberxy * numberxy * 2 samples,one is [0:blockz,:,:],two is [-blockz-1:-1,:,:]
    if stridez == 0:
        nb_sub_images = numberxy * numberxy * 2
        hr_samples = np.empty(shape=(nb_sub_images, blockz, block_width, block_height), dtype=np.float32)
        indx = 0
        for x in range(0, width - block_width + 1, stridewidth):
            for y in range(0, height - block_height + 1, strideheight):
                hr_samples[indx, :, :, :] = image[0:blockz, x:x + block_width, y:y + block_height]
                indx += 1
                hr_samples[indx, :, :, :] = image[-blockz - 1:-1, x:x + block_width, y:y + block_height]
                indx += 1
        if (indx != nb_sub_images):
            print(indx)
            print(nb_sub_images)
            raise ValueError("error sub number image")
        return hr_samples


def make_patch(image, patch_block_size, numberxy, numberz):
    """
    make number patch
    :param image:[depth,512,512]
    :param patch_block: such as[64,128,128]
    :return:[samples,64,128,128]
    expand the dimension z range the subimage:[startpostion-blockz//2:endpostion+blockz//2,:,:]
    """
    image_subsample = subimage_generator(image=image, patch_block_size=patch_block_size, numberxy=numberxy,
                                         numberz=numberz)
    return image_subsample


def gen_image_mask(srcimg, seg_image, index, shape, numberxy, numberz, trainImage, trainMask):
    # step1 remove not region
    start_pos, end_pos = getRangImageDepth(seg_image)
    if end_pos - start_pos > np.array(shape)[0]:
        end_pos = end_pos + np.array(shape)[0] // 4
        start_pos = start_pos - np.array(shape)[0] // 4
        if start_pos < 0:
            start_pos = 0
        if end_pos >= np.shape(seg_image)[0]:
            end_pos = np.shape(seg_image)[0] - 1
    else:
        step = end_pos - start_pos
        end_pos = end_pos + step
        start_pos = start_pos - step
        if start_pos < 0:
            start_pos = 0
        if end_pos >= np.shape(seg_image)[0]:
            end_pos = np.shape(seg_image)[0] - 1
    print((start_pos, end_pos))
    # step 2 get subimages (numberxy*numberxy*numberz,64, 128, 128)
    srcimg = srcimg[start_pos:end_pos, :, :]
    seg_image = seg_image[start_pos:end_pos, :, :]
    sub_srcimages = make_patch(srcimg, patch_block_size=shape, numberxy=numberxy, numberz=numberz)
    sub_liverimages = make_patch(seg_image, patch_block_size=shape, numberxy=numberxy, numberz=numberz)
    # step 3 only save subimages (numberxy*numberxy*numberz,64, 128, 128)
    samples, imagez = np.shape(sub_srcimages)[0], np.shape(sub_srcimages)[1]
    for j in range(samples):
        sub_masks = sub_liverimages.astype(np.float32)
        sub_masks = np.clip(sub_masks, 0, 255).astype('uint8')
        if np.max(sub_masks[j, :, :, :]) == 255:
            filepath = trainImage + "\\" + str(index) + "_" + str(j) + ".npy"
            filepath2 = trainMask + "\\" + str(index) + "_" + str(j) + ".npy"
            image = sub_srcimages[j, :, :, :]
            image = image.astype(np.float32)
            image = np.clip(image, 0, 255).astype('uint8')
            np.save(filepath, image)
            np.save(filepath2, sub_masks[j, :, :, :])


def prepare3dtraindata(srcpath, maskpath, trainImage, trainMask, number, height, width, shape=(16, 256, 256),
                       numberxy=3, numberz=20):
    for i in range(0, number, 1):
        index = 0
        listsrc = []
        listmask = []
        for _ in os.listdir(srcpath + str(i)):
            image = cv2.imread(srcpath + str(i) + "/" + str(index) + ".bmp", cv2.IMREAD_GRAYSCALE)
            image = cv2.resize(image, (width, height))
            label = cv2.imread(maskpath + str(i) + "/" + str(index) + ".bmp", cv2.IMREAD_GRAYSCALE)
            label = cv2.resize(label, (width, height))
            listsrc.append(image)
            listmask.append(label)
            index += 1

        imagearray = np.array(listsrc)
        imagearray = np.reshape(imagearray, (index, height, width))
        maskarray = np.array(listmask)
        maskarray = np.reshape(maskarray, (index, height, width))
        gen_image_mask(imagearray, maskarray, i, shape=shape, numberxy=numberxy, numberz=numberz, trainImage=trainImage,
                       trainMask=trainMask)


def preparetraindata():
    """
    0-199 for trained,200-209 for testing
    :return:
    """
    height = 512
    width = 512
    number = 210
    # srcpath = "E:\junqiangchen\data\kits19\kits19process\Image\\"
    # maskpath = "E:\junqiangchen\data\kits19\kits19process\Mask\\"
    # trainImage = "E:\junqiangchen\data\kits19\kits19segmentation\Image"
    # trainMask = "E:\junqiangchen\data\kits19\kits19segmentation\Mask"
    srcpath = "D:\Data\kits19\kits19tumorprocess\Image\\"
    maskpath = "D:\Data\kits19\kits19tumorprocess\Mask\\"
    trainImage = "D:\Data\kits19\kits19tumor3dsegmentation\Image"
    trainMask = "D:\Data\kits19\kits19tumor3dsegmentation\Mask"
    prepare3dtraindata(srcpath, maskpath, trainImage, trainMask, number, height, width, (64, 128, 128), 6, 16)


#preparetraindata()