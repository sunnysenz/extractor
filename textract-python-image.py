#Analyzes text in a document stored in an S3 bucket. Display polygon box around text and angled text
import boto3
import io
from io import BytesIO
import sys

document = sys.argv[1]

import math
from PIL import Image, ImageDraw, ImageFont

import demo_rows

def DrawBoundingBox(draw,box,width,height,boxColor,text=None,bold=False):
    left = width * box['Left']
    top = height * box['Top']
    bottom = top + (height * box['Height'])
    fill = None
    fontcolor = (0,0,180,255)
    # if text:
    #     fill = (200,200,200,200)

    draw.rectangle([left,top, left + (width * box['Width']), bottom],outline=boxColor, fill=fill)
    if bold:
      offsets = [1, 2]
      for offset in offsets:
        draw.rectangle(
            [left - offset, top - offset, left + (width * box['Width']) + offset, bottom + offset],
            outline=boxColor, fill=fill)
    if text:
        fontsize = min(40, int(bottom - top - 2))
        print('*** drawing text:', fontsize, text)
        draw.text((left, top), text, fill=(0,0,180,255),
          font=ImageFont.truetype('/Library/Fonts/Arial.ttf', fontsize))

# Displays information about a block returned by text detection and text analysis
def DisplayBlockInformation(block):
    print('Id: {}'.format(block['Id']))
    if 'Text' in block:
        print('    Detected: ' + block['Text'])
    print('    Type: ' + block['BlockType'])

    if 'Confidence' in block:
        print('    Confidence: ' + "{:.2f}".format(block['Confidence']) + "%")

    if block['BlockType'] == 'CELL':
        print("    Cell information")
        print("        Column:" + str(block['ColumnIndex']))
        print("        Row:" + str(block['RowIndex']))
        print("        Column Span:" + str(block['ColumnSpan']))
        print("        RowSpan:" + str(block['ColumnSpan']))

    if 'Relationships' in block:
        print('    Relationships: {}'.format(block['Relationships']))
    print('    Geometry: ')
    print('        Bounding Box: {}'.format(block['Geometry']['BoundingBox']))
    print('        Polygon: {}'.format(block['Geometry']['Polygon']))

    if block['BlockType'] == "KEY_VALUE_SET":
        print ('    Entity Type: ' + block['EntityTypes'][0])
    if 'Page' in block:
        print('Page: ' + block['Page'])
    print()

if __name__ == "__main__":
    # Test code - view s3 connect
    ec2 = boto3.client('ec2', region_name='us-east-1')

    idesc = ec2.describe_instances()
    # print(idesc)
    # Call S3 to list current buckets
    # Create an S3 client
    s3 = boto3.client('s3')
    response = s3.list_buckets()

    # Get a list of all bucket names from the response
    buckets = [bucket['Name'] for bucket in response['Buckets']]

    # Print out the bucket list
    print("Bucket List: %s" % buckets)
    # end test code

    bucket="evaltextract"

    #Get the document from S3
    s3_connection = boto3.resource('s3', region_name='us-east-1')

    s3_object = s3_connection.Object(bucket,document)
    s3_response = s3_object.get()

    stream = io.BytesIO(s3_response['Body'].read())
    image=Image.open(stream)

    # Analyze the document
    client = boto3.client('textract', region_name='us-east-1')

    image_binary = stream.getvalue()
    response = client.analyze_document(Document={'Bytes': image_binary},
        FeatureTypes=["TABLES", "FORMS"])

    # Alternatively, process using S3 object
    #response = client.analyze_document(
    #    Document={'S3Object': {'Bucket': bucket, 'Name': document}},
    #    FeatureTypes=["TABLES", "FORMS"])


    #Get the text blocks
    blocks=response['Blocks']
    width, height = image.size
    draw = ImageDraw.Draw(image)
    canvas = Image.new('RGB', (width, height), color = 'white')
    canvas_draw = ImageDraw.Draw(canvas)
    print ('Detected Document Text')

    # Create image showing bounding box/polygon the detected lines/text
    for block in blocks:
        DisplayBlockInformation(block)
        # demo_rows.ExtractBlockRow(block)
        draw=ImageDraw.Draw(image)
        if block['BlockType'] == "KEY_VALUE_SET":
            if block['EntityTypes'][0] == "KEY":
                DrawBoundingBox(draw, block['Geometry']['BoundingBox'],width,height,'red')
            else:
                DrawBoundingBox(draw, block['Geometry']['BoundingBox'],width,height,'green')

        if block['BlockType'] == 'TABLE':
            DrawBoundingBox(draw, block['Geometry']['BoundingBox'],width,height, 'blue')

        if block['BlockType'] == 'CELL':
            DrawBoundingBox(draw, block['Geometry']['BoundingBox'],width,height, 'yellow')

        if block['BlockType'] == 'LINE':
            text = None
            # this line down to draw text over top of the existing doc.
            DrawBoundingBox(draw, block['Geometry']['BoundingBox'],width,height, 'orange', text)
            if 'Text' in block:
                text = block['Text']
            if canvas:
                DrawBoundingBox(canvas_draw, block['Geometry']['BoundingBox'],width,height, 'orange', text)

        # Highlignt individual words
        if block['BlockType'] == 'WORD' and 'Text' in block:
            filter = ['Padilla', 'Leonard', 'Dowda', 'Fields', 'Misty', 'Croslin',
                      'REEVES', 'JOE', 'JOE T', 'THORAX', 'CT THORAX']
            if any(word in block['Text'] for word in filter):
                DrawBoundingBox(draw, block['Geometry']['BoundingBox'],width,height, 'red', None, True)

            #uncomment to draw polygon for all Blocks
            #points=[]
            #for polygon in block['Geometry']['Polygon']:
            #    points.append((width * polygon['X'], height * polygon['Y']))
            #draw.polygon((points), outline='blue')

    # Dump csv rows
    # print('*** CSV ROWS ***')
    # RowsToCsv()
    # Display the image
    image.show()
    canvas.show()