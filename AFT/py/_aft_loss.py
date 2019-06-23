import  numpy  as np
from    scipy.stats import norm
import  math
from    multiprocessing.dummy import Pool as ThreadPool 

pool    = ThreadPool(2)

def _getEventType(y_lower, y_higher):
    
    if y_lower==y_higher:
        return 'uncensored'
    elif y_lower != -float('inf') and y_higher != float('inf'):
        return 'interval'
    elif y_lower == -float('inf'):
        return 'left'
    else:
        return 'right'

def _z(y, y_pred, sigma):
    z = (math.log(y)-y_pred)/sigma
    return z

def _f_z(z, dist = 'logistic'):
    if dist == 'logistic':
        f_z = math.exp(1)**z/(1+math.exp(1)**z)**2
    if dist == 'normal':
        f_z = norm.pdf(z)
    return f_z

def _grad_f_z(z, dist = 'logistic'):
    f_z = _f_z(z,dist)
    if dist == 'logistic':
        grad_f_z = f_z*(1-math.exp(1)**z)/(1+math.exp(1)**z)
    if dist == 'normal':
        grad_f_z = -z*f_z
    return grad_f_z

def _hes_f_z(z, dist = 'logistic'):
    f_z = _f_z(z,dist)
    if dist == 'logistic':
        w       = math.exp(1)**z
        hes_f_z = f_z*(w**2-4*w+1)/(1+w)**2 
    if dist == 'normal':
        hes_f_z = (z**2-1)*f_z  
    return hes_f_z

def _F_z(z, dist = 'logistic'):
    if dist=='logistic':
        F_z = math.exp(1)**z/(1+math.exp(1)**z)
    if dist=='normal':
        F_z = norm.cdf(z)
    return F_z

def _grad_F_z(z,dist):
    return f_z(z,dist)
    
def _f_y(z, y, sigma, dist = 'logistic'):
    f_y = _f_z(z,dist)/(y*sigma)
    return f_y

def _grad_f_y(z, y, sigma, dist = 'logistic'):
    grad_f_y = -_grad_f_z(z,dist)/(sigma**2*y)
    return f_y

def _neg_grad(y_lower, y_higher, y_pred, sigma, type = 'left', dist = 'normal'):
    
    if type=='uncensored':
        z   = (math.log(y_lower)-y_pred)/sigma
        f_z = _f_z(z,dist)
        _neg_grad = -_grad_f_z(z,dist)/(sigma*f_z)
        return _neg_grad
    if type=='left':
        z   = (math.log(y_higher)-y_pred)/sigma
        f_z = _f_z(z,dist)
        F_z = _F_z(z,dist)
        _neg_grad = -f_z/(sigma*F_z)
        return _neg_grad
    if type=='right':
        z   = (math.log(y_lower)-y_pred)/sigma
        f_z = _f_z(z,dist)
        F_z = _F_z(z,dist)
        _neg_grad = f_z/(sigma*(1-F_z))
        return _neg_grad
    if type=='interval':
        z_u           = (math.log(y_higher) - y_pred)/sigma
        z_l           = (math.log(y_lower) - y_pred)/sigma
        f_z_u         = _f_z(z_u,dist)
        f_z_l         = _f_z(z_l,dist)
        F_z_u         = _F_z(z_u,dist)
        F_z_l         = _F_z(z_l,dist)
        _neg_grad     = -(f_z_u-f_z_l)/(sigma*(F_z_u-F_z_l))
        return _neg_grad
    
def _loss(y_lower, y_higher, y_pred, sigma, type = 'left', dist = 'normal'):
    if type=='uncensored':
        z    = (math.log(y_lower)-y_pred)/sigma
        f_z  = _f_z(z,dist)
        cost = -math.log(f_z/(sigma*y_lower))
        return cost
    if type=='left':
        z    = (math.log(y_higher)-y_pred)/sigma
        F_z  = _F_z(z,dist)
        cost = -math.log(F_z)
        return cost
    if type=='right':
        z   = (math.log(y_lower)-y_pred)/sigma
        F_z = _F_z(z,dist)
        cost= -math.log(1-F_z)
        return cost
    if type=='interval':
        z_u   = (math.log(y_higher) - y_pred)/sigma
        z_l   = (math.log(y_lower) - y_pred)/sigma
        f_z_u = _f_z(z_u,dist)
        f_z_l = _f_z(z_l,dist)
        F_z_u = _F_z(z_u,dist)
        F_z_l = _F_z(z_l,dist)
        cost  = -math.log(F_z_u - F_z_l)
        return cost

def _hessian(y_lower, y_higher, y_pred, sigma, type = 'left', dist = 'normal'):
    
    if type=='uncensored':
        z        = (math.log(y_lower)-y_pred)/sigma
        f_z      = _f_z(z,dist)
        grad_f_z = _grad_f_z(z,dist)
        hes_f_z  = _hes_f_z(z,dist)
        hess     = -(f_z*hes_f_z - grad_f_z**2)/(sigma**2*f_z**2)
        return hess
    
    if type=='left':
        z        = (math.log(y_higher)-y_pred)/sigma
        f_z      = _f_z(z,dist)
        F_z      = _F_z(z,dist)
        grad_f_z = _grad_f_z(z,dist)
        hess     = -(F_z*grad_f_z-f_z**2)/(sigma**2*F_z**2)
        return hess
    
    if type=='right':
        z        = (math.log(y_lower)-y_pred)/sigma
        f_z      = _f_z(z,dist)
        F_z      = _F_z(z,dist)
        grad_f_z = _grad_f_z(z,dist)
        hess     = -((1-F_z)*grad_f_z+f_z**2)/(sigma**2*(1-F_z)**2)
        return hess
    
    if type=='interval':
        z_u        = (math.log(y_higher) - y_pred)/sigma
        z_l        = (math.log(y_lower) - y_pred)/sigma
        f_z_u      = f_z(z_u,dist)
        f_z_l      = f_z(z_l,dist)
        F_z_u      = F_z(z_u,dist)
        F_z_l      = F_z(z_l,dist)
        grad_f_z_u = _grad_f_z(z_u,dist)
        grad_f_z_l = _grad_f_z(z_l,dist) 
        hess       = ((F_z_u-F_z_l)*(grad_f_z_u+grad_f_z_l)-(f_z_u**2-f_z_l**2))/(sigma**2*(F_z_u-F_z_l)**2)
        return hess
    

def negative_gradient(y_lower, y_higher, y_pred, dist, sigma):
    
    # Notation Convention
    # eta = Xb
    # This is original Equation
    # log(y_pred) = Xb
    # Here
    # eta = y_pred
    # Actual Predicted = exp^(Xb)
    
    n          = len(y_lower)
    sigma_rep  = np.repeat(sigma,n)
    dist_rep   = np.repeat(dist,n)
    event      = list(pool.starmap(_getEventType,zip(y_lower,y_higher)))
    #print(event)
    neg_grad   = list(pool.starmap(_neg_grad,zip(y_lower,y_higher,y_pred,sigma_rep,event,dist_rep)))
    
    return neg_grad

def loss(y_lower, y_higher, y_pred, dist, sigma):
    
    n          = len(y_lower)
    sigma_rep  = np.repeat(sigma,n)
    dist_rep   = np.repeat(dist,n)
    event      = list(pool.starmap(_getEventType,zip(y_lower,y_higher)))
    #loss      = list(pool.starmap(_loss,zip(y_lower,y_higher,y_pred,sigma_rep,event,dist_rep)))
    loss       = []
    for i in range(n):
        print(y_lower[i],y_higher[i],y_pred[i],sigma_rep[i],event[i],dist_rep[i])
        print('\n')
        loss.append(_loss(y_lower[i],y_higher[i],y_pred[i],sigma_rep[i],event[i],dist_rep[i]))
    return loss

def hessian(y_lower, y_higher, y_pred, dist, sigma):
    
    n          = len(y_lower)
    sigma_rep  = np.repeat(sigma,n)
    dist_rep   = np.repeat(dist,n)
    event      = list(pool.starmap(_getEventType,zip(y_lower,y_higher)))
    hessian    = list(pool.starmap(_hessian,zip(y_lower,y_higher,y_pred,sigma_rep,event,dist_rep)))
    return hessian

    