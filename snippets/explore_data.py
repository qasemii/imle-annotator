import csv
# from utils.preprocess_eSNLI import csv_to_txt

# csv file name
file_dir = "esnli_train_1.csv"
file = open(file_dir)

rows = csv.DictReader(file)

sentences, labels, highlights = [], [], []
for row in rows:
    premise, hypothesis = row['Sentence1'], row['Sentence2']
    sentence = premise + ' ' + hypothesis
    label = row['gold_label']

    highlighted_premise, highlighted_hypothesis = row['Sentence1_marked_1'], row['Sentence2_marked_1']
    l1, l2 = len(highlighted_premise.split('*'))//2, len(highlighted_hypothesis.split('*'))//2

    premise_highlights = [highlighted_premise.split('*')[2*i + 1] for i in range(l1)]
    hypothesis_highlights = [highlighted_hypothesis.split('*')[2*i + 1] for i in range(l2)]
    highlight = premise_highlights + hypothesis_highlights

    sentences.append(sentence)
    labels.append(label)
    highlights.append(highlight)



# print(len(sentences))
# print(len(labels))
# print(len(highlights))
