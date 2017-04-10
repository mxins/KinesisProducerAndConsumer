#!env python
'''
Copyright 2014-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Amazon Software License (the "License").
You may not use this file except in compliance with the License.
A copy of the License is located at

http://aws.amazon.com/asl/

or in the "license" file accompanying this file. This file is distributed
on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
express or implied. See the License for the specific language governing
permissions and limitations under the License.
'''
from __future__ import print_function
import sys, random, time, argparse
from boto import kinesis

def get_stream_status(conn, stream_name):
    '''
    Query this provided connection object for the provided stream's status.

    :type conn: boto.kinesis.layer1.KinesisConnection
    :param conn: A connection to Amazon Kinesis

    :type stream_name: str
    :param stream_name: The name of a stream.

    :rtype: str
    :return: The stream's status
    '''
    r = conn.describe_stream(stream_name)
    description = r.get('StreamDescription')
    return description.get('StreamStatus')

def wait_for_stream(conn, stream_name):
    '''
    Wait for the provided stream to become active.

    :type conn: boto.kinesis.layer1.KinesisConnection
    :param conn: A connection to Amazon Kinesis

    :type stream_name: str
    :param stream_name: The name of a stream.
    '''
    SLEEP_TIME_SECONDS = 3
    status = get_stream_status(conn, stream_name)
    while status != 'ACTIVE':
        print('{stream_name} has status: {status}, sleeping for {secs} seconds'.format(
                stream_name = stream_name,
                status      = status,
                secs        = SLEEP_TIME_SECONDS))
        time.sleep(SLEEP_TIME_SECONDS) # sleep for 3 seconds
        status = get_stream_status(conn, stream_name)

def put_word_in_stream(conn, stream_name, w):
    '''
    Put each word in the provided list of words into the stream.

    :type conn: boto.kinesis.layer1.KinesisConnection
    :param conn: A connection to Amazon Kinesis

    :type stream_name: str
    :param stream_name: The name of a stream.

    :type words: list
    :param words: A list of strings to put into the stream.
    '''
    try:
        conn.put_record(stream_name, w, w)
        with open('producer.data', 'a+') as f:
            f.write(w + "\n")
        print("Put word: " + w + " at:%d into stream: " % int(time.time())+ stream_name)
    except Exception as e:
        sys.stderr.write("Encountered an exception while trying to put a word: "
                         + w + " into stream: " + stream_name + " exception was: " + str(e))

def put_words_in_stream_periodically(conn, stream_name):
    '''
    Puts words into a stream, then waits for the period to elapse then puts the words in again. There is no strict
    guarantee about how frequently we put each word into the stream, just that we will wait between iterations.

    :type conn: boto.kinesis.layer1.KinesisConnection
    :param conn: A connection to Amazon Kinesis

    :type stream_name: str
    :param stream_name: The name of a stream.

    :type words: list
    :param words: A list of strings to put into the stream.

    :type period_seconds: int
    :param period_seconds: How long to wait, in seconds, between iterations over the list of words.
    '''
    period_seconds = 1
    idx = 1
    start = int(time.time())
    while True:
        put_word_in_stream(conn, stream_name, '%d-%r-%r' % (idx, start, int(time.time())))
        print("Sleeping for {period_seconds} seconds".format(period_seconds=period_seconds))
        time.sleep(period_seconds)
        idx += 1
        if idx > 10000:
            break

if __name__ == '__main__':
    stream_name = "debug-stream"
    region = "us-east-1"

    '''
    Getting a connection to Amazon Kinesis will require that you have your credentials available to
    one of the standard credentials providers.
    '''
    print("Connecting to stream: {s} in {r}".format(s=stream_name, r=region))
    conn = kinesis.connect_to_region(region_name = region)
    try:
        status = get_stream_status(conn, stream_name)
        if 'DELETING' == status:
            print('The stream: {s} is being deleted, please rerun the script.'.format(s=stream_name))
            sys.exit(1)
        elif 'ACTIVE' != status:
            wait_for_stream(conn, stream_name)
    except:
        # We'll assume the stream didn't exist so we will try to create it with just one shard
        conn.create_stream(stream_name, 1)
        wait_for_stream(conn, stream_name)
    # Now the stream should exist
    # if len(args.words) == 0:
    #     print('No -w options provided. Waiting on input from STDIN')
    #     words = [l.strip() for l in sys.stdin.readlines() if l.strip() != '']
    # else:
    #     words = args.words
    put_words_in_stream_periodically(conn, stream_name)
