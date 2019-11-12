from hmm import HMM
from MultivariateGaussian import MultivariateGaussian
import numpy as np
class GaussianHMM(HMM):

    # (super)保存隐含状态数目，初始化初始状态概率，状态转移概率
    # (GaussianHMM) 初始化观测值维度，每个状态发射概率为高斯分布——初始化均值和方差
    def __init__(self, initial_prob, transition_prob, means, covs):
        super().__init__(initial_prob, transition_prob)
        self.n_dim = means.shape[1]
        self.means = means
        self.covs = covs
        self.precisions = np.linalg.inv(self.covs) # 协方差矩阵的逆矩阵,通常称为精度矩阵(precision matrix)
    
    # 参数(pi, A, B)中已经有了pi, A, 由于是连续的发射概率, B未显式给定，下面根据连续分布函数求离散的B
    # 命名原因: '似然'的含义：计算生成数据的概率; 此处的'似然'的含义: 假设发射概率为多维高斯分布，计算每时刻每种状态生成给定观测值的概率
    # input  X, X[t] = ot
    #           X.shape = (T, n_dim).
    # return B, B[t, i] = P(ot|zt = i)
    #           B.shape = (T, n_hidden).
    def likelihood(self, X):
        
        # diff = X[:,None,:] - self.means  给定时刻t， 计算ot与每个状态发射均值的差值，所以要先扩展X，使之在时刻t有n_hidden个相同的值，再分别减去各状态的发射均值
        T = X.shape[0]
        diff = np.zeros((T, self.n_hidden, self.n_dim))   
        for t in range(T):
            for i in range(self.n_hidden):
                diff[t][i] = X[t] - self.means[i]
        
        likelihood = np.zeros((T, self.n_hidden))
        for t in range(T):
            for i in range(self.n_hidden):
                likelihood[t][i] = MultivariateGaussian(self.means[i], self.covs[i]).prob(X[t])  # t时刻, 第i个状态的高斯分布生成该时刻观测值X[t]的概率
        
        return likelihood
    
    '''
    params:
        Qs       (num, T_k)
        epsilons (num, T_k, n_hidden, n_hidden)
        gammas   (num, T_k, n_hidden)
    update:
        initial_prob[i] = gamma(1,i)
                 shape  = (n_hidden, )
        transition_prob[i,j] = sum_t epsilon_t(i, j) / sum_t gamma_t(i)
                 shape  = (n_hidden, n_hidden)
        means[i] = ui = sum_t gamma(t, i) * ot / sum_t gamma(t, i)
                      = gamma(,i) X Q / sum_t gamma(t, i)
    '''
    def maximize(self, Qs, epsilons, gammas):
        
        num = len(Qs)
        self.initial_prob = np.zeros(self.n_hidden)
        for k in range(num):
            self.initial_prob += gammas[k][0][:]
        self.initial_prob /= num
        

        self.transition_prob = sum([epsilon.sum(axis = 0) for epsilon in epsilons]) # 先对每个epsilon分别求和, 在把这些加起来
        self.transition_prob /= sum([gamma.sum(axis = 0) for gamma in gammas]) # 矩阵求和时axis = 0, 表示将每行加和得到一行

        for i in range(self.n_hidden):
            ui = sum([np.matmul(gamma[:,i], Q) for Q, gamma in zip(Qs, gammas)]) / num
            self.means[i] = ui
            #print(gammas[0][:,i].shape) (100,) 每个时刻出现状态i的概率 T维数组
            #print((Qs[0] - ui).shape)   (100,2) 每时刻与状态i方差的差值向量， T*n_dim维
            covs = np.zeros((self.n_hidden, self.n_dim, self.n_dim))
            for k in range(num):
                Q = Qs[k]
                T = Q.shape[0]
                gamma = gammas[k]
                for t in range(T):
                    for i in range(self.n_hidden):
                        diff = Q[t] - self.means[i]
                        diff.shape = (1, diff.shape[0])
                        covs[i] += gamma[t][i] * np.matmul(diff.T, diff)
            #print(sum([gamma.sum(axis = 0) for gamma in gammas]).shape): (3,) 没问题
            #print(covs.shape): (3,2,2) 没问题
            sum_gamma = sum([gamma.sum(axis = 0) for gamma in gammas])
            for i in range(self.n_hidden):
                covs[i] /= (sum_gamma[i] + 1e-2/self.n_hidden)
            # covi = sum([np.matmul(gamma[:,i], np.matmul((Q - ui).T, Q - ui)) for Q, gamma in zip(Qs, gammas)]) / num
            self.covs = covs
        
        return
