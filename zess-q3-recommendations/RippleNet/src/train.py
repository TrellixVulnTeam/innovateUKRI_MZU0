import numpy as np
import torch
import time
import pickle
from model import RippleNet


def train(args, data_info, show_loss):
    train_data = data_info[0]
    eval_data = data_info[1]
    test_data = data_info[2]
    n_entity = data_info[3]
    n_relation = data_info[4]
    ripple_set = data_info[5]

    model = RippleNet(args, n_entity, n_relation)
    if not args.use_cuda:
        model.cuda()
    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        args.lr,
    )
    for step in range(args.n_epoch):
        # training
        np.random.shuffle(train_data)
        start = 0
        while start < train_data.shape[0]:
            return_dict = model(
                *get_feed_dict(
                    args, model, train_data, ripple_set, start, start + args.batch_size
                )
            )
            loss = return_dict["loss"]

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            start += args.batch_size
            if show_loss:
                print("%.1f%% %.4f" % (start / train_data.shape[0] * 100, loss.item()))

        # evaluation
        train_auc, train_acc, train_scores = evaluation(
            model, train_data, (args, ripple_set, args.batch_size)
        )
        eval_auc, eval_acc, eval_scores = evaluation(
            model, eval_data, (args, ripple_set, args.batch_size)
        )
        test_auc, test_acc, test_scores = evaluation(
            model, test_data, (args, ripple_set, args.batch_size)
        )

        print(
            "epoch %d    train auc: %.4f  acc: %.4f    eval auc: %.4f  acc: %.4f    test auc: %.4f  acc: %.4f"
            % (step, train_auc, train_acc, eval_auc, eval_acc, test_auc, test_acc)
        )
    # print("test_scores: ", test_scores)
    # print("test_data: ", test_data)

    return test_data, test_scores


def get_feed_dict(args, model, data, ripple_set, start, end):
    items = torch.LongTensor(data[start:end, 1])
    labels = torch.LongTensor(data[start:end, 2])

    # time.sleep(1000)
    memories_h, memories_r, memories_t = [], [], []
    for i in range(args.n_hop):
        # for user in data[start:end, 0]:
        #     print(ripple_set[user][i][1])
        #     time.sleep(1000)
        memories_h.append(
            torch.LongTensor([ripple_set[user][i][0] for user in data[start:end, 0]])
        )
        memories_r.append(
            torch.LongTensor([ripple_set[user][i][1] for user in data[start:end, 0]])
        )
        memories_t.append(
            torch.LongTensor([ripple_set[user][i][2] for user in data[start:end, 0]])
        )
    if not args.use_cuda:
        items = items.cuda()
        labels = labels.cuda()
        memories_h = list(map(lambda x: x.cuda(), memories_h))
        memories_r = list(map(lambda x: x.cuda(), memories_r))
        memories_t = list(map(lambda x: x.cuda(), memories_t))

    return items, labels, memories_h, memories_r, memories_t


def evaluation(model, data, params):
    args = params[0]
    ripple_set = params[1]
    batch_size = params[2]
    start = 0
    auc_list = []
    acc_list = []
    scores_list = []
    model.eval()
    while start < data.shape[0]:
        auc, acc, scores = model.evaluate(
            *get_feed_dict(args, model, data, ripple_set, start, start + batch_size)
        )
        auc_list.append(auc)
        acc_list.append(acc)
        scores_list.append(scores)
        start += batch_size
    model.train()

    torch.save(
        model,
        "../../data/py_model.pkl",
        )

    model_params = (args, ripple_set, batch_size)
    pickle.dump((data, model_params), open("save.pkl", "wb"))

    return float(np.mean(auc_list)), float(np.mean(acc_list)), scores_list
